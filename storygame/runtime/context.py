"""Bounded prompt context assembled exclusively from RuntimeState."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from storygame.authoring.causal_contracts import InteractionFrame, NpcMovementPlan, Storylet
from storygame.runtime.narrative import StoryletSelector
from storygame.runtime.pacing import PaceDirective, PacingController
from storygame.runtime.state import RuntimeState

PROMPT_VERSION = "runtime-v2-turn-v2"


@dataclass(frozen=True)
class RuntimeContext:
    prompt_version: str
    token_estimate: int
    payload: dict[str, Any]


class RuntimeContextBuilder:
    def __init__(self, pacing: PacingController | None = None, event_limit: int = 12) -> None:
        self.pacing = pacing or PacingController()
        self.event_limit = event_limit

    def build(self, state: RuntimeState, player_input: str) -> RuntimeContext:
        active = state.active_beats
        storylets = StoryletSelector(state.narrative_package, state.facts).select(
            active_beat_ids=tuple(beat.id for beat in active), location_id=state.world.location
        )
        current_targets = _current_targets(state)
        active_interaction = _active_interaction(state)
        directives: list[PaceDirective] = [
            self.pacing.directive(
                beat,
                turns_active=state.beat_runtime[beat.id].turns_active,
                stagnant_turns=state.beat_runtime[beat.id].stagnant_turns,
            )
            for beat in active
        ]
        payload = {
            "player_input": player_input,
            "world": {
                "location": state.world.location,
                "flags": sorted(state.world.flags),
                "attributes": state.world.attributes,
                "items": state.world.items,
            },
            "facts": _player_visible_facts(state),
            "current_targets": current_targets,
            "speaker_private_context": _speaker_private_context(state, current_targets["participants"]),
            "summary": state.story_summary,
            "progression": {
                "scene_purpose": state.compiled_story.scene_purpose,
                "dramatic_question": state.compiled_story.dramatic_question,
                "pressure": _fact_value(state, "scene_pressure", "scene"),
                "goals": [item.model_dump(mode="json") for item in state.compiled_story.goals],
                "tasks": [item.model_dump(mode="json") for item in state.compiled_story.tasks],
                "clues": [item.model_dump(mode="json") for item in state.compiled_story.clues],
                "relationships": [item.model_dump(mode="json") for item in state.compiled_story.relationships],
                "timed_events": [item.model_dump(mode="json") for item in state.compiled_story.timed_events],
                "endings": [item.model_dump(mode="json") for item in state.compiled_story.endings],
            },
            "recent_events": [event.__dict__ for event in state.recent_events[-self.event_limit :]],
            "active_beats": [
                {"id": beat.id, "completion_tags": [tag.id for tag in beat.completion_tags]} for beat in active
            ],
            "narrative_opportunities": {
                "active_situation": _active_situation(state),
                "active_interaction": active_interaction,
                "storylets": [
                    _storylet_context(storylet)
                    for storylet in storylets
                    if active_interaction is None or storylet.id != active_interaction["storylet_id"]
                ],
                "freeform_allowed": True,
            },
            "protections": [
                {"id": item.id, "reveal_after": item.reveal_after}
                for item in state.compiled_story.protected_revelations
            ],
            "pace_directives": [directive.__dict__ for directive in directives],
            "turn_result_contract": {
                "narration": "non-empty player-visible prose",
                "operations": "array of {kind,path,value}; use [] when no state change",
                "operation_kinds": ["set", "add", "remove"],
                "operation_paths": [
                    "world.location (set string)",
                    "world.flags (add/remove string)",
                    "world.attributes.<name> (set)",
                    "world.items.<item_id>.holder (set string)",
                    "facts (add/remove typed assertable fact)",
                ],
                "beat_updates": "array of {beat_id,completion_tags,evidence}; use [] when no beat completes",
                "completion_tag_rule": (
                    "copy only the exact completion_tags listed for the matching active beat; otherwise use []"
                ),
                "storylet_realization": {
                    "storylet_id": "optional selected eligible narrative_opportunities.storylets id",
                    "realization_mode": "one declared realization_modes value",
                    "consequence_ids": "subset of that storylet's declared consequence_ids",
                    "completion_evidence": "use the storylet completion truth only after its consequence commits it",
                    "abort_evidence": (
                        "use only declared abort truth ids; this opens declared failure-forward opportunities"
                    ),
                },
                "material_progress": "boolean",
                "dialogue": {
                    "target_id": "the declared visible NPC addressed by the player",
                    "speaker_id": "must equal target_id",
                    "permitted_context": "fact ids the speaker is allowed to use",
                    "dialogue": "spoken NPC response, not a narrator substitution",
                    "effects": "bounded StateOperation objects committed before rendering",
                },
            },
        }
        if state.turn_index == 0:
            payload["opening"] = _opening_context(state)
        payload["turn_guidance"] = _turn_guidance(state)
        encoded = json.dumps(payload, default=list, separators=(",", ":"))
        return RuntimeContext(PROMPT_VERSION, max(1, len(encoded) // 4), payload)


def _active_situation(state: RuntimeState) -> dict[str, object] | None:
    spine = state.narrative_package.dramatic_spine if state.narrative_package is not None else None
    if spine is None:
        return None
    return {
        "conflict": spine.active_conflict,
        "question": spine.central_question,
        "pressure": spine.target_pressure.model_dump(),
    }


def _player_visible_facts(state: RuntimeState) -> list[dict[str, object]]:
    package = state.narrative_package
    protected = package.protected_truth_ids if package is not None else frozenset()
    current = _current_targets(state)
    visible_ids = {
        item["id"]
        for category in ("participants", "scene_subjects", "evidence", "groups")
        for item in current[category]
        if isinstance(item.get("id"), str)
    }
    declared_ids = (
        {
            item.id
            for collection in (
                package.participants,
                package.scene_subjects,
                package.evidence_realizations,
                package.group_encounters,
            )
            for item in collection
        }
        if package is not None
        else set()
    )
    return [
        fact.model_dump(mode="json")
        for fact in sorted(state.facts.asserted, key=lambda item: item.key)
        if not (fact.predicate == "knows" and fact.subject != "player")
        and fact.predicate not in {"motive", "stance"}
        and not (fact.object in protected and fact.subject != "player")
        and not (fact.value in protected and fact.subject != "player")
        and not (fact.subject in declared_ids and fact.subject not in visible_ids)
    ]


def _current_targets(state: RuntimeState) -> dict[str, list[dict[str, object]]]:
    package = state.narrative_package
    if package is None:
        return {"participants": [], "scene_subjects": [], "evidence": [], "groups": [], "movement_plans": []}
    location = state.world.location
    participants: list[dict[str, object]] = [
        {
            "id": participant.id,
            "public_name": participant.public_name,
            "public_role": participant.public_role,
            "public_description": participant.public_description,
        }
        for participant in package.participants
        if state.facts.has("present", participant.id, location)
        and state.facts.has("npc_availability", participant.id, value="present")
    ]
    subjects: list[dict[str, object]] = [
        {
            "id": subject.id,
            "kind": subject.kind,
            "public_description": subject.public_description,
        }
        for subject in package.scene_subjects
        if state.facts.has("at", subject.id, location) and state.facts.has("inspectable", subject.id, value="true")
    ]
    evidence: list[dict[str, object]] = [
        {
            "id": realization.id,
            "kind": realization.kind,
            "public_description": realization.public_description,
            "scene_subject_id": realization.scene_subject_id,
        }
        for realization in package.evidence_realizations
        if state.facts.has("at", realization.id, location)
    ]
    groups: list[dict[str, object]] = [
        {"id": encounter.id, "label": encounter.label, "participant_ids": list(encounter.participant_ids)}
        for encounter in package.group_encounters
        if state.facts.has("group_at", encounter.id, location)
        and all(state.facts.has("present", participant_id, location) for participant_id in encounter.participant_ids)
    ]
    plans: list[dict[str, object]] = [
        {
            "id": plan.id,
            "participant_id": plan.participant_id,
            "destination_location_id": plan.destination_location_id,
            "player_may_accompany": plan.player_may_accompany,
        }
        for plan in package.movement_plans
        if _movement_plan_is_eligible(state, plan)
    ]
    return {
        "participants": participants,
        "scene_subjects": subjects,
        "evidence": evidence,
        "groups": groups,
        "movement_plans": plans,
    }


def _movement_plan_is_eligible(state: RuntimeState, plan: NpcMovementPlan) -> bool:
    return bool(
        state.facts.has("at", plan.participant_id, plan.source_location_id)
        and state.facts.has("npc_availability", plan.participant_id, value="present")
        and all(state.facts.has("knows", "player", truth_id) for truth_id in plan.activation_truth_ids)
        and not any(state.facts.has("knows", "player", truth_id) for truth_id in plan.abort_truth_ids)
    )


def _speaker_private_context(
    state: RuntimeState, participants: list[dict[str, object]]
) -> dict[str, dict[str, object]]:
    package = state.narrative_package
    if package is None:
        return {}
    profiles = {profile.participant_id: profile for profile in package.npc_performance_profiles}
    truths = {truth.id: truth.summary for truth in package.truths}
    contexts: dict[str, dict[str, object]] = {}
    for participant in participants:
        participant_id = participant["id"]
        if not isinstance(participant_id, str):
            continue
        known_truth_ids = sorted(
            fact.object for fact in state.facts.matching("knows", participant_id) if fact.object is not None
        )
        private_facts = [
            fact.model_dump(mode="json")
            for fact in state.facts.asserted
            if fact.predicate in {"motive", "relationship", "stance"}
            and (fact.subject == participant_id or fact.object == participant_id)
        ]
        profile = profiles.get(participant_id)
        contexts[participant_id] = {
            "performance_profile": profile.model_dump(mode="json") if profile is not None else None,
            "known_truth_ids": known_truth_ids,
            "known_truths": [
                {"id": truth_id, "summary": truths[truth_id]} for truth_id in known_truth_ids if truth_id in truths
            ],
            "private_facts": sorted(private_facts, key=lambda item: str(item)),
            "recent_interactions": _recent_interactions(state, participant_id),
        }
    return contexts


def _recent_interactions(state: RuntimeState, participant_id: str) -> list[dict[str, object]]:
    package = state.narrative_package
    if package is None:
        return []
    return [
        {
            "frame_id": frame.id,
            "active": _interaction_marker(state, "interaction_active", frame.id),
            "completed": _interaction_marker(state, "interaction_completed", frame.id),
            "aborted": _interaction_marker(state, "interaction_aborted", frame.id),
            "recently_used": _interaction_marker(state, "interaction_recently_used", frame.id),
        }
        for frame in package.interaction_frames
        if participant_id == frame.initiator_id or participant_id in frame.participant_ids
    ]


def _interaction_marker(state: RuntimeState, predicate: str, frame_id: str) -> bool:
    return state.facts.has(predicate, frame_id, value="true")


def _active_interaction(state: RuntimeState) -> dict[str, object] | None:
    package = state.narrative_package
    if package is None:
        return None
    for frame in sorted(package.interaction_frames, key=lambda item: item.id):
        participants_present = all(
            participant_id == "player" or state.facts.has("present", participant_id, state.world.location)
            for participant_id in frame.participant_ids
        )
        if (
            _interaction_marker(state, "interaction_active", frame.id)
            and not _interaction_marker(state, "interaction_completed", frame.id)
            and not _interaction_marker(state, "interaction_aborted", frame.id)
            and state.world.location in frame.location_ids
            and participants_present
            and state.facts.has("npc_availability", frame.initiator_id, value="present")
        ):
            return _interaction_context(frame)
    return None


def _interaction_context(frame: InteractionFrame) -> dict[str, object]:
    return {
        "id": frame.id,
        "storylet_id": frame.storylet_id,
        "initiator_id": frame.initiator_id,
        "participant_ids": list(frame.participant_ids),
        "initiation": frame.initiation,
        "dramatic_objective": frame.dramatic_objective,
        "opening_move": frame.opening_move,
        "response_obligations": list(frame.response_obligations),
        "allowed_tactics": list(frame.allowed_tactics),
        "agency_modes": list(frame.agency_modes),
        "permitted_movement_plan_ids": list(frame.permitted_movement_plan_ids),
    }


def _storylet_context(storylet: Storylet) -> dict[str, object]:
    return {
        "id": storylet.id,
        "purpose": storylet.purpose,
        "dramatic_question": storylet.dramatic_question,
        "realization_modes": list(storylet.realization_modes),
        "consequence_ids": list(storylet.consequence_ids),
    }


def _fact_value(state: RuntimeState, predicate: str, subject: str) -> str | None:
    matches = state.facts.matching(predicate, subject)
    return matches[0].value if matches else None


def _turn_guidance(state: RuntimeState) -> dict[str, object]:
    if state.turn_index == 0:
        return {
            "opening_turn": True,
            "narration_requirement": (
                "Establish the current place and public situation, then address the player's action."
            ),
        }
    return {
        "opening_turn": False,
        "narration_requirement": (
            "Address the player's current action from the current state; do not repeat the opening orientation "
            "unless the player explicitly asks to look."
        ),
    }


def _opening_context(state: RuntimeState) -> dict[str, Any]:
    """Expose only package-declared public orientation for the opening turn."""

    declared = state.world.attributes.get("opening_context", {})
    if isinstance(declared, dict):
        public_facts = declared.get("public_facts", [])
        if not public_facts:
            public_facts = _legacy_public_facts(state.world.attributes)
        if not public_facts:
            public_facts = [state.compiled_story.premise]
        navigation = state.world.attributes.get("navigation", {})
        routes = navigation.get("routes", []) if isinstance(navigation, dict) else []
        destinations = [
            route.get("to", "").replace("_", " ")
            for route in routes
            if isinstance(route, dict) and route.get("from") == state.world.location
        ]
        opening = state.compiled_story.opening
        typed = opening.model_dump(mode="json") if opening is not None else {}
        return {
            "premise": state.compiled_story.premise,
            "public_facts": public_facts,
            "current_location": state.world.location,
            "available_destinations": declared.get("available_destinations") or destinations,
            "first_beat": "Investigate the opening situation and choose a lead.",
            **declared,
            **typed,
            "protected_boundaries": [
                {"id": item.id, "summary": item.summary, "reveal_after": item.reveal_after}
                for item in state.compiled_story.protected_revelations
            ],
        }
    return {
        "premise": state.compiled_story.premise,
        "public_facts": [],
        "current_location": state.world.location,
        "available_destinations": [],
        "first_beat": "Investigate the opening situation and choose a lead.",
        "protected_boundaries": [
            {"id": item.id, "summary": item.summary, "reveal_after": item.reveal_after}
            for item in state.compiled_story.protected_revelations
        ],
    }


def _legacy_public_facts(attributes: dict[str, Any]) -> list[str]:
    facts: list[str] = []
    situation = attributes.get("opening_situation")
    if isinstance(situation, str) and situation:
        facts.append(situation)
    briefing = attributes.get("public_briefing")
    if isinstance(briefing, dict):
        facts.extend(value for value in briefing.values() if isinstance(value, str) and value)
    return facts
