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
            "world": {
                "location": state.world.location,
                "flags": sorted(state.world.flags),
                "attributes": state.world.attributes,
                "items": state.world.items,
            },
            "summary": state.story_summary,
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
                ],
                "beat_updates": "array of {beat_id,completion_tags,evidence}; use [] when no beat completes",
                "completion_tag_rule": (
                    "copy only the exact completion_tags listed for the matching active beat; otherwise use []"
                ),
                "material_progress": "boolean",
            },
        }
        encoded = json.dumps(payload, default=list, separators=(",", ":"))
        return RuntimeContext(PROMPT_VERSION, max(1, len(encoded) // 4), payload)
