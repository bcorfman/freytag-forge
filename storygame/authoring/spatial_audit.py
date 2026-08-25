"""Read-only characterization of the causal blueprint-to-runtime spatial loss."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from storygame.authoring.contracts import CompiledStory
from storygame.runtime.state import RuntimeState, bootstrap_runtime_state

TargetKind = Literal["present_npc", "group_encounter", "visible_item", "scene_subject"]


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
    compiled_story: CompiledStory,
    *,
    participant_ids: tuple[str, ...] | None = None,
    evidence_opportunity_ids: tuple[str, ...] = (),
    scene_subject_ids: tuple[str, ...] = (),
    group_encounter_ids: tuple[str, ...] = (),
) -> RuntimeProjectionAudit:
    """Measure current fact-backed targets without inventing replacement state."""

    state = bootstrap_runtime_state(compiled_story)
    declared_participants = participant_ids or tuple(character.id for character in compiled_story.characters)
    placed_participants = tuple(
        participant_id for participant_id in declared_participants if _is_placed(state, participant_id)
    )
    realized_evidence = tuple(
        opportunity_id for opportunity_id in evidence_opportunity_ids if opportunity_id in state.world.items
    )
    custody_backed = tuple(
        opportunity_id for opportunity_id in evidence_opportunity_ids if state.facts.matching("custody", opportunity_id)
    )
    participant_placements = _coverage(declared_participants, placed_participants)
    scene_subjects = _coverage(scene_subject_ids, ())
    evidence_realization = _coverage(evidence_opportunity_ids, realized_evidence)
    evidence_custody = _coverage(evidence_opportunity_ids, custody_backed)
    group_encounters = _coverage(group_encounter_ids, ())
    suggested_actions = _audit_suggested_actions(state)
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
    locations = {fact.object for fact in state.facts.matching("at", participant_id) if fact.object is not None}
    return any(state.facts.has("present", participant_id, location) for location in locations)


def _audit_suggested_actions(state: RuntimeState) -> tuple[SuggestedActionAudit, ...]:
    opening = state.compiled_story.opening
    if opening is None:
        return ()
    targets = _current_target_aliases(state)
    return tuple(_audit_suggested_action(action, targets) for action in opening.first_available_actions)


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
