"""Immutable, locally validated causal-story-v2 authoring contracts.

These declarations are offline authoring input.  They deliberately do not
describe runtime effects or mutable state.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from storygame.authoring.symbol_resolution import Namespace, SymbolRegistry, SymbolResolutionError

_ID = r"^[a-z][a-z0-9_]*$"


class CausalValidationError(ValueError):
    """A semantic rejection for an immutable causal candidate."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceProvenance(_Contract):
    source_format: Literal["story-outline-inventory-v1", "freytag-story-brief-v1"]
    source_id: str = Field(min_length=1, max_length=120)
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_path: str | None = Field(default=None, min_length=1)
    source_schema_version: str | None = Field(default=None, min_length=1, max_length=80)
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=160)
    response_id: str | None = Field(default=None, min_length=1, max_length=200)
    prompt_version: str | None = Field(default=None, min_length=1, max_length=80)
    validation_results: tuple[str, ...] = Field(default=(), max_length=64)


class Truth(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    roles: tuple[str, ...] = Field(default=(), max_length=16)


class Participant(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    role: str = Field(min_length=1, max_length=80)


class Location(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    role: str = Field(min_length=1, max_length=80)
    initial_access: bool = False


class ConnectedRoute(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    from_location_id: str = Field(pattern=_ID, max_length=80)
    to_location_id: str = Field(pattern=_ID, max_length=80)
    aliases: tuple[str, ...] = Field(min_length=1, max_length=16)
    prerequisite_truths: tuple[str, ...] = Field(default=(), max_length=16)


class CausalEvent(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    actor_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    location_id: str = Field(pattern=_ID, max_length=80)
    input_truths: tuple[str, ...] = Field(default=(), max_length=32)
    output_truths: tuple[str, ...] = Field(min_length=1, max_length=32)
    earliest: int = Field(ge=0, le=100000)
    latest: int = Field(ge=0, le=100000)
    prerequisite_event_ids: tuple[str, ...] = Field(default=(), max_length=32)


class TimelineConstraint(_Contract):
    before_event_id: str = Field(pattern=_ID, max_length=80)
    after_event_id: str = Field(pattern=_ID, max_length=80)


class EvidenceOpportunity(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    truth_id: str = Field(pattern=_ID, max_length=80)
    kind: str = Field(min_length=1, max_length=80)
    holder_id: str = Field(pattern=_ID, max_length=80)
    location_id: str = Field(pattern=_ID, max_length=80)
    supports: bool = True
    route_id: str = Field(pattern=_ID, max_length=80)


class PartyKnowledge(_Contract):
    participant_id: str = Field(pattern=_ID, max_length=80)
    truth_ids: tuple[str, ...] = Field(default=(), max_length=64)


class KnowledgeProtection(_Contract):
    truth_id: str = Field(pattern=_ID, max_length=80)
    release_after_revelation_ids: tuple[str, ...] = Field(min_length=1, max_length=16)


class FailureForward(_Contract):
    consequence_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    alternative_route_ids: tuple[str, ...] = Field(default=(), max_length=16)


class RealizationRoute(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    revelation_id: str = Field(pattern=_ID, max_length=80)
    opportunity_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    prerequisite_truths: tuple[str, ...] = Field(default=(), max_length=16)
    prerequisite_revelation_ids: tuple[str, ...] = Field(default=(), max_length=16)
    result_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    failure_forward: FailureForward


class Revelation(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    truth_id: str = Field(pattern=_ID, max_length=80)
    required: bool = True
    gate_beat_ids: tuple[str, ...] = Field(default=(), max_length=16)


class RequiredOutcome(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    truth_id: str = Field(pattern=_ID, max_length=80)


class Beat(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    phase: str = Field(min_length=1, max_length=80)
    required_outcome_id: str | None = Field(default=None, pattern=_ID, max_length=80)
    prerequisite_revelation_ids: tuple[str, ...] = Field(default=(), max_length=16)
    pressure: int = Field(ge=0, le=100)


class OptionalBeat(Beat):
    purpose: Literal["alternative_satisfier", "complication", "relationship_development", "world_development"]


class SuspectHypothesis(_Contract):
    participant_id: str = Field(pattern=_ID, max_length=80)
    supporting_truth_ids: tuple[str, ...] = Field(min_length=2, max_length=16)
    exonerating_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=16)


class EndState(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    required_outcome_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    required_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=32)


class CausalCompiledStory(_Contract):
    """The Phase-1 ``story-blueprint-v2`` candidate contract."""

    schema_version: Literal["story-blueprint-v2"]
    id: str = Field(pattern=_ID, max_length=80)
    version: int = Field(ge=1, le=9999)
    provenance: SourceProvenance
    genre: str = Field(min_length=1, max_length=80)
    profile: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    premise: str = Field(min_length=1, max_length=1200)
    opening_truth_ids: tuple[str, ...] = Field(default=(), max_length=64)
    truths: tuple[Truth, ...] = Field(min_length=1, max_length=128)
    participants: tuple[Participant, ...] = Field(min_length=1, max_length=64)
    locations: tuple[Location, ...] = Field(min_length=1, max_length=64)
    connected_routes: tuple[ConnectedRoute, ...] = Field(default=(), max_length=128)
    causal_events: tuple[CausalEvent, ...] = Field(min_length=1, max_length=128)
    timeline_constraints: tuple[TimelineConstraint, ...] = Field(default=(), max_length=128)
    evidence_opportunities: tuple[EvidenceOpportunity, ...] = Field(min_length=1, max_length=128)
    party_knowledge: tuple[PartyKnowledge, ...] = Field(default=(), max_length=64)
    knowledge_protections: tuple[KnowledgeProtection, ...] = Field(default=(), max_length=64)
    revelations: tuple[Revelation, ...] = Field(min_length=1, max_length=64)
    realization_routes: tuple[RealizationRoute, ...] = Field(min_length=1, max_length=128)
    required_outcomes: tuple[RequiredOutcome, ...] = Field(min_length=1, max_length=64)
    required_beats: tuple[Beat, ...] = Field(min_length=1, max_length=64)
    optional_beats: tuple[OptionalBeat, ...] = Field(default=(), max_length=64)
    suspect_hypotheses: tuple[SuspectHypothesis, ...] = Field(default=(), max_length=32)
    end_states: tuple[EndState, ...] = Field(min_length=1, max_length=16)


def _acyclic(nodes: set[str], edges: Mapping[str, tuple[str, ...]], code: str) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise CausalValidationError(code, f"graph contains '{node}'")
        if node not in visited:
            visiting.add(node)
            for dependency in edges[node]:
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

    for node in nodes:
        visit(node)


def _validate_topology(story: CausalCompiledStory, truth_ids: set[str], location_ids: set[str]) -> None:
    route_ids = {route.id for route in story.connected_routes}
    for route in story.connected_routes:
        if len(set(route.aliases)) != len(route.aliases):
            raise CausalValidationError("DUPLICATE_ALIAS", f"route '{route.id}' repeats an alias")
    if not any(location.initial_access for location in story.locations):
        raise CausalValidationError("OPENING_LOCATION_REQUIRED", "one location needs initial access")
    aliases = [alias.casefold() for route in story.connected_routes for alias in route.aliases]
    if len(aliases) != len(set(aliases)):
        raise CausalValidationError("DUPLICATE_ALIAS", "route aliases must be unique")
    _ = route_ids


def _validate_events(
    story: CausalCompiledStory,
    truth_ids: set[str],
    participant_ids: set[str],
    location_ids: set[str],
) -> None:
    event_ids = {event.id for event in story.causal_events}
    for event in story.causal_events:
        if event.earliest > event.latest:
            raise CausalValidationError("TIMELINE_INVALID", f"event '{event.id}' ends before it begins")
    _acyclic(event_ids, {event.id: event.prerequisite_event_ids for event in story.causal_events}, "CAUSAL_CYCLE")
    by_id = {event.id: event for event in story.causal_events}
    infeasible: list[str] = []
    for constraint in story.timeline_constraints:
        if by_id[constraint.before_event_id].latest > by_id[constraint.after_event_id].earliest:
            infeasible.append(f"{constraint.before_event_id}->{constraint.after_event_id}")
    if infeasible:
        raise CausalValidationError("TIMELINE_INVALID", f"infeasible timeline constraints: {', '.join(infeasible)}")


def _reachable_locations(story: CausalCompiledStory) -> set[str]:
    reachable = {location.id for location in story.locations if location.initial_access}
    available_truths = set(story.opening_truth_ids)
    changed = True
    while changed:
        changed = False
        for event in story.causal_events:
            if set(event.input_truths) <= available_truths:
                new_truths = set(event.output_truths) - available_truths
                if new_truths:
                    available_truths.update(new_truths)
                    changed = True
        for route in story.connected_routes:
            if (
                route.from_location_id in reachable
                and set(route.prerequisite_truths) <= available_truths
                and route.to_location_id not in reachable
            ):
                reachable.add(route.to_location_id)
                changed = True
            if (
                route.to_location_id in reachable
                and set(route.prerequisite_truths) <= available_truths
                and route.from_location_id not in reachable
            ):
                reachable.add(route.from_location_id)
                changed = True
    return reachable


def _validate_authoring_graph(story: CausalCompiledStory, truth_ids: set[str], participant_ids: set[str]) -> None:
    outcome_ids = {outcome.id for outcome in story.required_outcomes}
    required_beat_ids = {beat.id for beat in story.required_beats}
    optional_ids = {beat.id for beat in story.optional_beats}
    if required_beat_ids & optional_ids:
        raise CausalValidationError("DUPLICATE_ID", "a beat cannot be required and optional")
    hypothesis_participants = [hypothesis.participant_id for hypothesis in story.suspect_hypotheses]
    if len(hypothesis_participants) != len(set(hypothesis_participants)):
        raise CausalValidationError("DUPLICATE_ID", "suspect hypotheses repeat a participant")
    for hypothesis in story.suspect_hypotheses:
        if set(hypothesis.supporting_truth_ids) & set(hypothesis.exonerating_truth_ids):
            raise CausalValidationError(
                "SUSPECT_HYPOTHESIS_INVALID", f"suspect hypothesis '{hypothesis.participant_id}' reuses its evidence"
            )
    for route in story.realization_routes:
        failure_completes_route = set(route.failure_forward.consequence_truth_ids) & set(route.result_truth_ids)
        if not failure_completes_route and not route.failure_forward.alternative_route_ids:
            raise CausalValidationError("FAILURE_FORWARD_DEAD_END", f"route '{route.id}' cannot fail forward")
        selected_opportunities = (
            opportunity for opportunity in story.evidence_opportunities if opportunity.id in route.opportunity_ids
        )
        if any(opportunity.route_id != route.id for opportunity in selected_opportunities):
            raise CausalValidationError("CUSTODY_INCOMPATIBLE", f"route '{route.id}' does not hold its opportunity")
    incomplete_alternative_satisfiers = [
        optional.id
        for optional in story.optional_beats
        if optional.purpose == "alternative_satisfier" and optional.required_outcome_id is None
    ]
    if incomplete_alternative_satisfiers:
        beat_list = ", ".join(f"'{beat_id}'" for beat_id in incomplete_alternative_satisfiers)
        raise CausalValidationError("OPTIONAL_BEAT_INCOMPLETE", f"optional beats {beat_list} need an outcome")
    required_outcomes = {beat.required_outcome_id for beat in story.required_beats}
    for optional in story.optional_beats:
        if optional.purpose == "alternative_satisfier" and optional.required_outcome_id not in required_outcomes:
            raise CausalValidationError(
                "OPTIONAL_ONLY_REQUIRED_OUTCOME", f"optional beat '{optional.id}' is the sole route"
            )
    _validate_endings(story, outcome_ids, truth_ids)


def _validate_endings(story: CausalCompiledStory, outcome_ids: set[str], truth_ids: set[str]) -> None:
    for end_state in story.end_states:
        if set(outcome_ids) - set(end_state.required_outcome_ids):
            raise CausalValidationError("ENDING_NOT_VIABLE", f"end state '{end_state.id}' omits an outcome")


def validate_causal_compiled_story(payload: Mapping[str, object] | CausalCompiledStory) -> CausalCompiledStory:
    """Parse and prove generic structural/map/knowledge invariants locally."""

    try:
        story = payload if isinstance(payload, CausalCompiledStory) else CausalCompiledStory.model_validate(payload)
    except ValidationError as exc:
        diagnostics = tuple(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['type']}" for error in exc.errors()[:20]
        )
        suffix = " (additional contract errors omitted)" if len(exc.errors()) > len(diagnostics) else ""
        raise CausalValidationError("CONTRACT_INVALID", f"{' ; '.join(diagnostics)}{suffix}") from exc
    try:
        registry = SymbolRegistry.from_story(story)
        registry.bind(SymbolRegistry.reference_sites(story))
    except SymbolResolutionError as exc:
        duplicate = any(item.code == "DUPLICATE_SYMBOL" for item in exc.diagnostics)
        code = "DUPLICATE_ID" if duplicate else "UNKNOWN_REFERENCE"
        if all(item.path.startswith("evidence_opportunities[") for item in exc.diagnostics):
            legacy = "invalid opportunity references: " + ", ".join(
                f"{story.evidence_opportunities[int(item.path.split('[', 1)[1].split(']', 1)[0])].id}."
                f"{item.path.rsplit('.', 1)[-1]}->{item.supplied_id}"
                for item in exc.diagnostics
            )
            detail = (
                legacy
                if all(item.path.endswith("].route_id") for item in exc.diagnostics)
                else legacy + "; " + "; ".join(item.render() for item in exc.diagnostics)
            )
        else:
            detail = "; ".join(item.render() for item in exc.diagnostics)
        if any(item.path.startswith("party_knowledge[") for item in exc.diagnostics):
            detail += "; party knowledge reference uses a foreign namespace; use the mapped declared truth ID"
        raise CausalValidationError(code, detail) from exc
    truth_ids = set(registry.ids(Namespace.TRUTH))
    participant_ids = set(registry.ids(Namespace.PARTICIPANT))
    location_ids = set(registry.ids(Namespace.LOCATION))
    _validate_topology(story, truth_ids, location_ids)
    _validate_events(story, truth_ids, participant_ids, location_ids)
    _validate_authoring_graph(story, truth_ids, participant_ids)
    reachable = _reachable_locations(story)
    blocked = [item.id for item in story.evidence_opportunities if item.location_id not in reachable]
    if blocked:
        raise CausalValidationError("LOCATION_UNREACHABLE", f"opportunities are unreachable: {', '.join(blocked)}")
    return story
