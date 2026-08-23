"""Typed mutable runtime authority for the V2 engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from storygame.authoring.contracts import Beat, CompiledStory


@dataclass
class WorldState:
    location: str
    flags: set[str] = field(default_factory=set)
    attributes: dict[str, Any] = field(default_factory=dict)
    items: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class BeatRuntime:
    beat_id: str
    completed_tags: set[str] = field(default_factory=set)
    turns_active: int = 0
    stagnant_turns: int = 0


@dataclass(frozen=True)
class RuntimeEvent:
    turn_index: int
    player_input: str
    narration: str
    operations: tuple[dict[str, Any], ...]
    beat_updates: tuple[dict[str, Any], ...]
    prompt_version: str
    prompt_token_estimate: int


@dataclass
class RuntimeState:
    compiled_story: CompiledStory
    world: WorldState
    beat_runtime: dict[str, BeatRuntime]
    turn_index: int = 0
    recent_events: list[RuntimeEvent] = field(default_factory=list)
    story_summary: str = ""

    @property
    def active_beats(self) -> tuple[Beat, ...]:
        completed = {beat_id for beat_id, runtime in self.beat_runtime.items() if runtime.completed_tags}
        return tuple(
            beat
            for beat in self.compiled_story.beats
            if beat.id not in completed and all(prerequisite in completed for prerequisite in beat.prerequisites)
        )


def bootstrap_runtime_state(compiled_story: CompiledStory) -> RuntimeState:
    """Realize a reviewed immutable story into the only mutable V2 state object."""

    if not isinstance(compiled_story, CompiledStory):
        raise TypeError("runtime bootstrap requires a reviewed CompiledStory fixture")
    initial = compiled_story.initial_world_state
    location = initial.get("location")
    if not isinstance(location, str) or not location:
        location = "opening"
    attributes = {key: value for key, value in initial.items() if key not in {"location", "flags", "items"}}
    if compiled_story.opening is not None:
        attributes["opening_facts"] = {
            "location": location,
            "contacts": [contact.model_dump(mode="json") for contact in compiled_story.opening.contacts],
            "public_briefing": list(compiled_story.opening.public_briefing),
            "scene_purpose": compiled_story.opening.scene_purpose,
        }
    flags = {value for value in initial.get("flags", []) if isinstance(value, str)}
    raw_items = initial.get("items", {})
    items = {key: dict(value) for key, value in raw_items.items() if isinstance(key, str) and isinstance(value, dict)}
    return RuntimeState(
        compiled_story=compiled_story,
        world=WorldState(location=location, flags=flags, attributes=attributes, items=items),
        beat_runtime={beat.id: BeatRuntime(beat_id=beat.id) for beat in compiled_story.beats},
    )


def runtime_state_bytes(state: RuntimeState) -> bytes:
    """Stable snapshot used for atomicity checks and later persistence integrity."""
    payload = {
        "compiled_story": state.compiled_story.model_dump(mode="json"),
        "world": {
            "location": state.world.location,
            "flags": sorted(state.world.flags),
            "attributes": state.world.attributes,
            "items": state.world.items,
        },
        "beat_runtime": {
            beat_id: {
                "completed_tags": sorted(runtime.completed_tags),
                "turns_active": runtime.turns_active,
                "stagnant_turns": runtime.stagnant_turns,
            }
            for beat_id, runtime in state.beat_runtime.items()
        },
        "turn_index": state.turn_index,
        "recent_events": [event.__dict__ for event in state.recent_events],
        "story_summary": state.story_summary,
    }
    return json.dumps(payload, sort_keys=True).encode()
