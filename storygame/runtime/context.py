"""Bounded prompt context assembled exclusively from RuntimeState."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

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
            "opening": _opening_context(state),
            "world": {
                "location": state.world.location,
                "flags": sorted(state.world.flags),
                "attributes": state.world.attributes,
                "items": state.world.items,
            },
            "facts": [fact.model_dump(mode="json") for fact in sorted(state.facts.asserted, key=lambda item: item.key)],
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
        encoded = json.dumps(payload, default=list, separators=(",", ":"))
        return RuntimeContext(PROMPT_VERSION, max(1, len(encoded) // 4), payload)


def _fact_value(state: RuntimeState, predicate: str, subject: str) -> str | None:
    matches = state.facts.matching(predicate, subject)
    return matches[0].value if matches else None


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
