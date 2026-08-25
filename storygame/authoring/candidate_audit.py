"""Repeatable, story-agnostic automated review of blueprint candidates."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from storygame.authoring.blueprint_compiler import BlueprintCompilation
from storygame.authoring.bound_ir import BoundBlueprint, bind_blueprint
from storygame.authoring.causal_contracts import CausalValidationError, validate_causal_compiled_story
from storygame.authoring.causal_critics import CausalCompletenessCritic, FreytagProgressionCritic, RouteFairnessCritic
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError, _causal_story_as_compiled_story
from storygame.authoring.spatial_audit import RuntimeProjectionAudit, audit_runtime_projection
from storygame.authoring.storylet_critics import (
    DramaticEscalationCritic,
    FailureForwardViabilityCritic,
    ParticipantContinuityCritic,
    ProtectedKnowledgeSafetyCritic,
    StoryletCoverageCritic,
)

CHECK_IDS = (
    "compiler_validation",
    "terminal_roles",
    "knowledge_boundaries",
    "route_diversity",
    "failure_forward",
    "map_and_custody",
)
CheckStatus = Literal["pass", "fail", "skipped"]


class AuditCheck(BaseModel):
    """One deterministic result in a candidate audit."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    status: CheckStatus
    diagnostics: tuple[str, ...] = ()


class StoryletCoverage(BaseModel):
    """Stable coverage counts for immutable storylet authoring data."""

    model_config = ConfigDict(frozen=True)

    by_beat: dict[str, int] = Field(default_factory=dict)
    by_purpose: dict[str, int] = Field(default_factory=dict)
    by_realization_mode: dict[str, int] = Field(default_factory=dict)
    by_route_family: dict[str, int] = Field(default_factory=dict)
    failure_forward_chains: tuple[tuple[str, ...], ...] = ()


class CandidateAuditReport(BaseModel):
    """JSON-safe audit projection; it is not a promotion or runtime artifact."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["story-blueprint-audit-v1"]
    candidate_filename: str = Field(min_length=1)
    candidate_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    checks: tuple[AuditCheck, ...]
    storylet_coverage: StoryletCoverage = Field(default_factory=StoryletCoverage)
    runtime_projection: RuntimeProjectionAudit | None = None

    @property
    def passed(self) -> bool:
        return all(check.status == "pass" for check in self.checks)


def audit_candidate(candidate_path: Path, profiles: CausalProfileRegistry) -> CandidateAuditReport:
    """Audit one candidate without modifying it or making provider requests."""

    try:
        raw = candidate_path.read_bytes()
        payload = json.loads(raw)
        compilation = BlueprintCompilation.model_validate(payload)
    except FileNotFoundError:
        return _failed_report(candidate_path, None, "candidate does not exist")
    except (json.JSONDecodeError, ValidationError) as exc:
        return _failed_report(candidate_path, hashlib.sha256(raw).hexdigest(), f"invalid candidate envelope: {exc}")

    candidate_sha = hashlib.sha256(raw).hexdigest()
    if not compilation.accepted:
        return _failed_report(candidate_path, candidate_sha, "candidate is locally rejected")

    try:
        story = validate_causal_compiled_story(compilation.story)
        profiles.validate(story)
        bound = bind_blueprint(story)
        critic_diagnostics = tuple(
            detail
            for critic in (
                CausalCompletenessCritic(),
                RouteFairnessCritic(profiles),
                FreytagProgressionCritic(profiles),
                StoryletCoverageCritic(profiles),
                DramaticEscalationCritic(),
                ParticipantContinuityCritic(),
                ProtectedKnowledgeSafetyCritic(),
                FailureForwardViabilityCritic(),
            )
            for detail in critic.critique(bound).diagnostics
        )
        runtime_projection = audit_runtime_projection(
            _causal_story_as_compiled_story(story),
            participant_ids=tuple(participant.id for participant in story.participants),
            evidence_opportunity_ids=tuple(opportunity.id for opportunity in story.evidence_opportunities),
        )
    except (CausalValidationError, CompilationError) as exc:
        return _failed_report(candidate_path, candidate_sha, str(exc))

    compiler_diagnostics = tuple(compilation.diagnostics) + critic_diagnostics
    checks = (
        _check("compiler_validation", compiler_diagnostics),
        _check("terminal_roles", _terminal_role_diagnostics(bound)),
        _check("knowledge_boundaries", _knowledge_diagnostics(bound)),
        _check("route_diversity", _route_diagnostics(bound, profiles)),
        _check("failure_forward", _failure_forward_diagnostics(bound)),
        _check("map_and_custody", _map_diagnostics(bound)),
    )
    return CandidateAuditReport(
        schema_version="story-blueprint-audit-v1",
        candidate_filename=candidate_path.name,
        candidate_sha256=candidate_sha,
        checks=checks,
        storylet_coverage=_storylet_coverage(story),
        runtime_projection=runtime_projection,
    )


def _failed_report(path: Path, candidate_sha: str | None, diagnostic: str) -> CandidateAuditReport:
    return CandidateAuditReport(
        schema_version="story-blueprint-audit-v1",
        candidate_filename=path.name,
        candidate_sha256=candidate_sha,
        checks=(AuditCheck(id="compiler_validation", status="fail", diagnostics=(diagnostic,)),)
        + tuple(AuditCheck(id=check_id, status="skipped") for check_id in CHECK_IDS[1:]),
    )


def _storylet_coverage(story: object) -> StoryletCoverage:
    """Project reviewed storylet inventory without deriving runtime state."""

    by_beat: dict[str, int] = {}
    by_purpose: dict[str, int] = {}
    by_mode: dict[str, int] = {}
    by_route_family: dict[str, int] = {}
    chains: list[tuple[str, ...]] = []
    for storylet in getattr(story, "storylets", ()):
        by_beat[storylet.beat_id] = by_beat.get(storylet.beat_id, 0) + 1
        by_purpose[storylet.purpose] = by_purpose.get(storylet.purpose, 0) + 1
        by_route_family[storylet.route_family] = by_route_family.get(storylet.route_family, 0) + 1
        for mode in storylet.realization_modes:
            by_mode[mode] = by_mode.get(mode, 0) + 1
        if storylet.failure_forward_storylet_ids:
            chains.append((storylet.id, *storylet.failure_forward_storylet_ids))
    return StoryletCoverage(
        by_beat=dict(sorted(by_beat.items())),
        by_purpose=dict(sorted(by_purpose.items())),
        by_realization_mode=dict(sorted(by_mode.items())),
        by_route_family=dict(sorted(by_route_family.items())),
        failure_forward_chains=tuple(sorted(chains)),
    )


def _check(check_id: str, diagnostics: tuple[str, ...]) -> AuditCheck:
    return AuditCheck(id=check_id, status="fail" if diagnostics else "pass", diagnostics=diagnostics)


def _terminal_role_diagnostics(bound: BoundBlueprint) -> tuple[str, ...]:
    diagnostics: list[str] = []
    for ending in bound.end_states:
        outcome_truths = {outcome.truth.id for outcome in ending.outcomes}
        ending_truths = {truth.id for truth in ending.truths}
        if not outcome_truths <= ending_truths:
            diagnostics.append(f"end state '{ending.id}' has outcomes whose truths are not required")
    return tuple(diagnostics)


def _knowledge_diagnostics(bound: BoundBlueprint) -> tuple[str, ...]:
    opening_ids = {truth.id for truth in bound.opening_truths}
    diagnostics = [
        f"protected truth '{protection.truth.id}' is in the opening boundary"
        for protection in bound.protections
        if protection.truth.id in opening_ids
    ]
    diagnostics.extend(
        f"protected truth '{protection.truth.id}' has no release revelation"
        for protection in bound.protections
        if not protection.revelations
    )
    return tuple(diagnostics)


def _route_diagnostics(bound: BoundBlueprint, profiles: CausalProfileRegistry) -> tuple[str, ...]:
    minimum = profiles.resolve(bound.story.profile).minimum_independent_proof_routes
    by_revelation: dict[str, set[str]] = {}
    for route in bound.realization_routes:
        by_revelation.setdefault(route.revelation.id, set()).update(item.kind for item in route.opportunities)
    return tuple(
        f"revelation '{revelation.id}' has {len(by_revelation.get(revelation.id, set()))} opportunity kinds; "
        f"requires {minimum}"
        for revelation in bound.revelations
        if revelation.declaration.required and len(by_revelation.get(revelation.id, set())) < minimum
    )


def _failure_forward_diagnostics(bound: BoundBlueprint) -> tuple[str, ...]:
    route_ids = {route.id for route in bound.realization_routes}
    diagnostics: list[str] = []
    for route in bound.realization_routes:
        if route.id in {alternative.id for alternative in route.alternatives}:
            diagnostics.append(f"route '{route.id}' points failure-forward to itself")
        if not route.alternatives and not route.failure_consequences:
            diagnostics.append(f"route '{route.id}' has neither a failure consequence nor an alternative route")
    if not route_ids:
        diagnostics.append("story has no realization routes")
    return tuple(diagnostics)


def _map_diagnostics(bound: BoundBlueprint) -> tuple[str, ...]:
    reachable = {location.id for location in bound.locations if location.declaration.initial_access}
    pending = deque(reachable)
    adjacency: dict[str, set[str]] = {}
    for route in bound.connected_routes:
        adjacency.setdefault(route.source.id, set()).add(route.destination.id)
    while pending:
        source = pending.popleft()
        for destination in adjacency.get(source, set()):
            if destination not in reachable:
                reachable.add(destination)
                pending.append(destination)
    diagnostics = [
        f"opportunity '{opportunity.id}' is at unreachable location '{opportunity.location.id}'"
        for opportunity in bound.evidence_opportunities
        if opportunity.location.id not in reachable
    ]
    return tuple(diagnostics)
