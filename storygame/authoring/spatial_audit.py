"""Read-only characterization of the causal blueprint-to-runtime spatial loss."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from storygame.authoring.contracts import CompiledStory
from storygame.runtime.narrative import RuntimeNarrativeProjection
from storygame.runtime.state import RuntimeState, bootstrap_runtime_state

TargetKind = Literal[
    "present_npc",
    "group_encounter",
    "visible_item",
    "scene_subject",
    "evidence_realization",
]


class ProjectionCoverage(BaseModel):
    """Declared identifiers compared with identifiers backed by runtime facts."""

    model_config = ConfigDict(frozen=True)

    declared_ids: tuple[str, ...] = ()
    fact_backed_ids: tuple[str, ...] = ()
    missing_ids: tuple[str, ...] = ()
    declared_count: int = 0
    fact_backed_count: int = 0


class SuggestedActionAudit(BaseModel):
    """One opening suggestion and the current targets that make it actionable."""

    model_config = ConfigDict(frozen=True)

    action: str
    target_ids: tuple[str, ...] = ()
    target_kinds: tuple[TargetKind, ...] = ()
    supported: bool


class RuntimeProjectionAudit(BaseModel):
    """Non-runtime evidence describing what survives the compatibility bridge."""

    model_config = ConfigDict(frozen=True)

    participant_placements: ProjectionCoverage
    scene_subjects: ProjectionCoverage
    evidence_realization: ProjectionCoverage
    evidence_custody: ProjectionCoverage
    group_encounters: ProjectionCoverage
    suggested_actions: tuple[SuggestedActionAudit, ...]
    unsupported_suggested_actions: tuple[str, ...]
    complete: bool


def audit_runtime_projection(
    compiled_story: CompiledStory | RuntimeNarrativeProjection,
    *,
    participant_ids: tuple[str, ...] | None = None,
    evidence_opportunity_ids: tuple[str, ...] = (),
    scene_subject_ids: tuple[str, ...] = (),
    group_encounter_ids: tuple[str, ...] = (),
    opening_suggestions: tuple[tuple[str, str, str], ...] = (),
) -> RuntimeProjectionAudit:
    """Measure current fact-backed targets without inventing replacement state."""

    state = bootstrap_runtime_state(compiled_story)
    package = state.narrative_package
    declared_participants = participant_ids or (
        tuple(participant.id for participant in package.participants)
        if package is not None
        else tuple(character.id for character in state.compiled_story.characters)
    )
    declared_scene_subjects = scene_subject_ids or (
        tuple(subject.id for subject in package.scene_subjects) if package is not None else ()
    )
    declared_evidence = evidence_opportunity_ids or (
        tuple(opportunity.id for opportunity in package.evidence_opportunities) if package is not None else ()
    )
    declared_groups = group_encounter_ids or (
        tuple(encounter.id for encounter in package.group_encounters) if package is not None else ()
    )
    placed_participants = tuple(
        participant_id for participant_id in declared_participants if _is_placed(state, participant_id)
    )
    realized_evidence = _realized_evidence(state, declared_evidence)
    custody_backed = _custody_backed_evidence(state, declared_evidence)
    realized_subjects = tuple(
        subject_id for subject_id in declared_scene_subjects if _is_scene_subject(state, subject_id)
    )
    realized_groups = tuple(group_id for group_id in declared_groups if _is_group_encounter(state, group_id))
    participant_placements = _coverage(declared_participants, placed_participants)
    scene_subjects = _coverage(declared_scene_subjects, realized_subjects)
    evidence_realization = _coverage(declared_evidence, realized_evidence)
    evidence_custody = _coverage(declared_evidence, custody_backed)
    group_encounters = _coverage(declared_groups, realized_groups)
    suggested_actions = _audit_suggested_actions(state, opening_suggestions)
    unsupported = tuple(action.action for action in suggested_actions if not action.supported)
    coverages = (
        participant_placements,
        scene_subjects,
        evidence_realization,
        evidence_custody,
        group_encounters,
    )
    return RuntimeProjectionAudit(
        participant_placements=participant_placements,
        scene_subjects=scene_subjects,
        evidence_realization=evidence_realization,
        evidence_custody=evidence_custody,
        group_encounters=group_encounters,
        suggested_actions=suggested_actions,
        unsupported_suggested_actions=unsupported,
        complete=not unsupported and all(not coverage.missing_ids for coverage in coverages),
    )


def _coverage(declared_ids: tuple[str, ...], fact_backed_ids: tuple[str, ...]) -> ProjectionCoverage:
    declared = tuple(dict.fromkeys(declared_ids))
    fact_backed = tuple(identifier for identifier in declared if identifier in set(fact_backed_ids))
    missing = tuple(identifier for identifier in declared if identifier not in set(fact_backed))
    return ProjectionCoverage(
        declared_ids=declared,
        fact_backed_ids=fact_backed,
        missing_ids=missing,
        declared_count=len(declared),
        fact_backed_count=len(fact_backed),
    )


def _is_placed(state: RuntimeState, participant_id: str) -> bool:
    return bool(state.facts.matching("at", participant_id))


def _realized_evidence(state: RuntimeState, opportunity_ids: tuple[str, ...]) -> tuple[str, ...]:
    package = state.narrative_package
    if package is None:
        return tuple(opportunity_id for opportunity_id in opportunity_ids if opportunity_id in state.world.items)
    return tuple(
        opportunity_id
        for opportunity_id in opportunity_ids
        if any(
            realization.evidence_opportunity_id == opportunity_id
            and state.facts.matching("evidence_kind", realization.id)
            and state.facts.matching("at", realization.id)
            for realization in package.evidence_realizations
        )
    )


def _custody_backed_evidence(state: RuntimeState, opportunity_ids: tuple[str, ...]) -> tuple[str, ...]:
    package = state.narrative_package
    if package is None:
        return tuple(
            opportunity_id for opportunity_id in opportunity_ids if state.facts.matching("custody", opportunity_id)
        )
    return tuple(
        opportunity_id
        for opportunity_id in opportunity_ids
        if any(
            realization.evidence_opportunity_id == opportunity_id and state.facts.matching("custody", realization.id)
            for realization in package.evidence_realizations
        )
    )


def _is_scene_subject(state: RuntimeState, subject_id: str) -> bool:
    return bool(
        state.facts.matching("scene_subject", subject_id)
        and state.facts.matching("at", subject_id)
        and state.facts.has("inspectable", subject_id, value="true")
    )


def _is_group_encounter(state: RuntimeState, group_id: str) -> bool:
    locations = tuple(fact.object for fact in state.facts.matching("group_at", group_id) if fact.object is not None)
    members = tuple(fact.object for fact in state.facts.matching("group_member", group_id) if fact.object is not None)
    return bool(locations and members) and all(
        state.facts.has("present", member_id, location) for location in locations for member_id in members
    )


def _audit_suggested_actions(
    state: RuntimeState, opening_suggestions: tuple[tuple[str, str, str], ...]
) -> tuple[SuggestedActionAudit, ...]:
    if opening_suggestions:
        return tuple(_audit_declared_suggestion(state, suggestion) for suggestion in opening_suggestions)
    opening = state.compiled_story.opening
    if opening is None:
        return ()
    targets = _current_target_aliases(state)
    return tuple(_audit_suggested_action(action, targets) for action in opening.first_available_actions)


def _audit_declared_suggestion(state: RuntimeState, suggestion: tuple[str, str, str]) -> SuggestedActionAudit:
    action, target_kind, target_id = suggestion
    target = _declared_target(state, target_kind, target_id)
    return SuggestedActionAudit(
        action=action,
        target_ids=(target_id,) if target is not None else (),
        target_kinds=(target,) if target is not None else (),
        supported=target is not None,
    )


def _declared_target(state: RuntimeState, target_kind: str, target_id: str) -> TargetKind | None:
    location = state.world.location
    if target_kind == "participant" and state.facts.has("present", target_id, location):
        return "present_npc"
    if (
        target_kind == "scene_subject"
        and _is_scene_subject(state, target_id)
        and _is_at_initially_accessible_location(state, target_id)
    ):
        return "scene_subject"
    if (
        target_kind == "evidence_realization"
        and state.facts.has("evidence_kind", target_id)
        and _is_at_initially_accessible_location(state, target_id)
    ):
        return "evidence_realization"
    if (
        target_kind == "group_encounter"
        and _is_group_encounter(state, target_id)
        and _is_at_initially_accessible_location(state, target_id, predicate="group_at")
    ):
        return "group_encounter"
    return None


def _is_at_initially_accessible_location(state: RuntimeState, target_id: str, *, predicate: str = "at") -> bool:
    package = state.narrative_package
    if package is None:
        return state.facts.has(predicate, target_id, state.world.location)
    initial_locations = {location.id for location in package.locations if location.initial_access}
    return any(
        fact.object in initial_locations
        for fact in state.facts.matching(predicate, target_id)
        if fact.object is not None
    )


def _audit_suggested_action(
    action: str, targets: tuple[tuple[str, TargetKind, tuple[str, ...]], ...]
) -> SuggestedActionAudit:
    matches = tuple((identifier, kind) for identifier, kind, aliases in targets if _mentions(action, aliases))
    return SuggestedActionAudit(
        action=action,
        target_ids=tuple(identifier for identifier, _ in matches),
        target_kinds=tuple(dict.fromkeys(kind for _, kind in matches)),
        supported=bool(matches),
    )


def _current_target_aliases(state: RuntimeState) -> tuple[tuple[str, TargetKind, tuple[str, ...]], ...]:
    targets: list[tuple[str, TargetKind, tuple[str, ...]]] = []
    for character in state.compiled_story.characters:
        if state.facts.has("present", character.id, state.world.location):
            targets.append((character.id, "present_npc", (character.id, character.name)))
    for item_id in _visible_item_ids(state):
        item = state.world.items[item_id]
        targets.append((item_id, "visible_item", (item_id, str(item.get("name", "")))))
    return tuple(targets)


def _visible_item_ids(state: RuntimeState) -> tuple[str, ...]:
    visible: list[str] = []
    for item_id, item in state.world.items.items():
        holder = item.get("holder")
        if holder in {"player", f"location:{state.world.location}"} or (
            isinstance(holder, str)
            and holder.startswith("npc:")
            and state.facts.has("present", holder.removeprefix("npc:"), state.world.location)
        ):
            visible.append(item_id)
    return tuple(visible)


def _mentions(action: str, aliases: tuple[str, ...]) -> bool:
    normalized_action = f" {_normalize(action)} "
    return any(alias and f" {_normalize(alias)} " in normalized_action for alias in aliases)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
