"""Deterministic Phase 3 critics for playable spatial conversations."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import cast

from storygame.authoring.bound_ir import BoundBlueprint
from storygame.authoring.causal_contracts import CausalCompiledStory, InteractionFrame, NpcMovementPlan
from storygame.authoring.causal_critics import CausalCriticResult


class SpatialContinuityCritic:
    """Require explicit, traversable actor, evidence, witness, and opening paths."""

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        story = cast(CausalCompiledStory, story.story) if isinstance(story, BoundBlueprint) else story
        if not _has_spatial_projection(story):
            return CausalCriticResult(
                "spatial_continuity",
                False,
                ("candidate has no playable spatial realization",),
            )

        reachable = _reachable_locations(story)
        participants = {item.id: item for item in story.participants}
        realizations = {item.evidence_opportunity_id: item for item in story.evidence_realizations}
        diagnostics: list[str] = []

        for event in story.causal_events:
            for actor_id in event.actor_ids:
                actor = participants[actor_id]
                if event.location_id not in reachable.get(actor.initial_location_id or "", set()):
                    diagnostics.append(
                        f"causal event '{event.id}' actor '{actor_id}' has no spatial path to '{event.location_id}'"
                    )
            _check_means_path(story, event.id, event.input_truths, event.location_id, reachable, diagnostics)

        for opportunity in story.evidence_opportunities:
            realization = realizations.get(opportunity.id)
            if realization is None:
                diagnostics.append(f"evidence opportunity '{opportunity.id}' has no playable realization")
                continue
            if not _reachable_from_opening(story, realization.location_id, reachable):
                diagnostics.append(f"evidence realization '{realization.id}' has no player-reachable evidence path")
            holder = participants[opportunity.holder_id]
            if realization.location_id not in reachable.get(holder.initial_location_id or "", set()):
                diagnostics.append(
                    f"evidence opportunity '{opportunity.id}' holder '{holder.id}' has no witness path to "
                    f"'{realization.location_id}'"
                )

        diagnostics.extend(_opening_interaction_diagnostics(story, reachable))
        return CausalCriticResult("spatial_continuity", not diagnostics, tuple(diagnostics))


class InteractionViabilityCritic:
    """Reject brittle, unsafe, or materially ungrounded dialogue situations."""

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        story = cast(CausalCompiledStory, story.story) if isinstance(story, BoundBlueprint) else story
        profiles = {item.id: item for item in story.npc_performance_profiles}
        movement_plans = {item.id: item for item in story.movement_plans}
        protected = _protected_summaries(story)
        diagnostics: list[str] = []

        dialogue_storylets = {item.id for item in story.storylets if "dialogue" in item.realization_modes}
        framed_storylets = {frame.storylet_id for frame in story.interaction_frames}
        for storylet_id in sorted(dialogue_storylets - framed_storylets):
            diagnostics.append(f"dialogue storylet '{storylet_id}' has no viable interaction frame")

        for frame in story.interaction_frames:
            initiator = next(item for item in story.participants if item.id == frame.initiator_id)
            if initiator.performance_profile_id not in profiles:
                diagnostics.append(
                    f"interaction frame '{frame.id}' initiator '{initiator.id}' has no complete performance profile"
                )
            if not frame.response_obligations:
                diagnostics.append(f"interaction frame '{frame.id}' has no response obligations and is a dead end")
            repeated = _duplicates(frame.allowed_tactics)
            diagnostics.extend(f"interaction frame '{frame.id}' repeats tactic '{item}'" for item in repeated)
            if len(set(frame.allowed_tactics)) < 2:
                diagnostics.append(f"interaction frame '{frame.id}' has fewer than two distinct tactics")
            if "engage" not in frame.agency_modes or not set(frame.agency_modes) & {
                "refuse",
                "redirect",
                "interrupt",
                "depart",
            }:
                diagnostics.append(f"interaction frame '{frame.id}' does not preserve participant agency")
            diagnostics.extend(_material_action_diagnostics(frame, movement_plans))
            diagnostics.extend(_protected_text_diagnostics(frame.id, frame, protected))

        return CausalCriticResult("interaction_viability", not diagnostics, tuple(diagnostics))


def _has_spatial_projection(story: CausalCompiledStory) -> bool:
    return bool(
        story.evidence_realizations and any(item.initial_location_id is not None for item in story.participants)
    )


def _reachable_locations(story: CausalCompiledStory) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for location in story.locations:
        graph[location.id].add(location.id)
    for route in story.connected_routes:
        graph[route.from_location_id].add(route.to_location_id)
        graph[route.to_location_id].add(route.from_location_id)
    for plan in story.movement_plans:
        graph[plan.source_location_id].add(plan.destination_location_id)

    return {location.id: _walk(graph, location.id) for location in story.locations}


def _walk(graph: dict[str, set[str]], origin: str) -> set[str]:
    visited: set[str] = set()
    pending = deque((origin,))
    while pending:
        current = pending.popleft()
        if current in visited:
            continue
        visited.add(current)
        pending.extend(graph[current] - visited)
    return visited


def _check_means_path(
    story: CausalCompiledStory,
    event_id: str,
    input_truth_ids: tuple[str, ...],
    event_location_id: str,
    reachable: dict[str, set[str]],
    diagnostics: list[str],
) -> None:
    for truth_id in input_truth_ids:
        sources = [item.location_id for item in story.evidence_opportunities if item.truth_id == truth_id]
        if sources and not any(event_location_id in reachable.get(source, set()) for source in sources):
            diagnostics.append(f"causal event '{event_id}' input truth '{truth_id}' has no spatial means path")


def _reachable_from_opening(story: CausalCompiledStory, location_id: str, reachable: dict[str, set[str]]) -> bool:
    return any(location_id in reachable[item.id] for item in story.locations if item.initial_access)


def _opening_interaction_diagnostics(story: CausalCompiledStory, reachable: dict[str, set[str]]) -> tuple[str, ...]:
    if story.opening is None:
        return ("candidate has no supported opening interaction declaration",)
    social = [
        item
        for item in story.opening.first_action_suggestions
        if item.target_kind in {"participant", "group_encounter"}
    ]
    if not social:
        return ("candidate has no supported opening social interaction",)
    participant_targets = {item.target_id for item in social if item.target_kind == "participant"}
    for item in social:
        if item.target_kind == "group_encounter":
            group = next(group for group in story.group_encounters if group.id == item.target_id)
            participant_targets.update(group.participant_ids)
    viable = any(
        frame.initiator_id in participant_targets
        and any(_reachable_from_opening(story, location_id, reachable) for location_id in frame.location_ids)
        for frame in story.interaction_frames
    )
    return () if viable else ("opening social target has no supported interaction frame",)


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    repeated: list[str] = []
    for value in values:
        if value in seen and value not in repeated:
            repeated.append(value)
        seen.add(value)
    return tuple(repeated)


def _protected_summaries(story: CausalCompiledStory) -> tuple[str, ...]:
    protected = {item.truth_id for item in story.knowledge_protections}
    return tuple(item.summary.casefold() for item in story.truths if item.id in protected)


def _material_action_diagnostics(frame: InteractionFrame, plans: dict[str, NpcMovementPlan]) -> tuple[str, ...]:
    for plan_id in frame.permitted_movement_plan_ids:
        plan = plans[plan_id]
        if plan.participant_id != frame.initiator_id or not {
            plan.source_location_id,
            plan.destination_location_id,
        } & set(frame.location_ids):
            return (f"interaction frame '{frame.id}' declares an unsupported material movement action",)
    return ()


def _protected_text_diagnostics(frame_id: str, frame: InteractionFrame, summaries: tuple[str, ...]) -> tuple[str, ...]:
    fields = (
        frame.dramatic_objective,
        frame.opening_move,
        *frame.response_obligations,
        *frame.allowed_tactics,
    )
    leaked = next((summary for summary in summaries if any(summary in value.casefold() for value in fields)), None)
    if leaked is None:
        return ()
    return (f"interaction frame '{frame_id}' exposes a protected truth in public performance guidance",)
