"""Minimal local validator and clone-first atomic state commit."""

from __future__ import annotations

import copy
import json
from typing import Any

from storygame.runtime.contracts import RuntimeFailure, TurnResult
from storygame.runtime.state import RuntimeState


def validate_and_commit(state: RuntimeState, result: TurnResult) -> RuntimeState:
    candidate = copy.deepcopy(state)
    _reject_protected_leaks(candidate, result)
    for operation in result.operations:
        _apply_operation(candidate, operation.kind, operation.path, operation.value)
    _apply_beat_updates(candidate, result)
    return candidate


def _apply_operation(state: RuntimeState, kind: str, path: str, value: Any) -> None:
    if path == "world.location" and kind == "set" and isinstance(value, str) and value:
        state.world.location = value
        return
    if path == "world.flags" and isinstance(value, str) and kind in {"add", "remove"}:
        (state.world.flags.add if kind == "add" else state.world.flags.discard)(value)
        return
    if path.startswith("world.attributes.") and kind == "set":
        state.world.attributes[path.removeprefix("world.attributes.")] = value
        return
    if path.startswith("world.items.") and path.endswith(".holder") and kind == "set" and isinstance(value, str):
        item_id = path.split(".")[2]
        item = state.world.items.setdefault(item_id, {})
        if "holder" in item and item["holder"] != value:
            raise RuntimeFailure("UNIQUE_CUSTODY_CONFLICT", f"item '{item_id}' already has a different holder")
        item["holder"] = value
        return
    raise RuntimeFailure("UNKNOWN_STATE_PATH", f"operation '{kind}' cannot modify '{path}'")


def _apply_beat_updates(state: RuntimeState, result: TurnResult) -> None:
    beats = {beat.id: beat for beat in state.compiled_story.beats}
    completed = {beat_id for beat_id, runtime in state.beat_runtime.items() if runtime.completed_tags}
    for update in result.beat_updates:
        beat = beats.get(update.beat_id)
        if beat is None:
            raise RuntimeFailure("UNKNOWN_BEAT", f"unknown beat '{update.beat_id}'")
        if not all(requirement in completed for requirement in beat.prerequisites):
            raise RuntimeFailure("INVALID_BEAT_ORDER", f"beat '{beat.id}' prerequisites are incomplete")
        allowed = {tag.id for tag in beat.completion_tags}
        if not set(update.completion_tags) <= allowed:
            raise RuntimeFailure("UNKNOWN_COMPLETION_TAG", f"beat '{beat.id}' received an undeclared completion tag")
        state.beat_runtime[beat.id].completed_tags.update(update.completion_tags)
        if update.completion_tags:
            completed.add(beat.id)


def _reject_protected_leaks(state: RuntimeState, result: TurnResult) -> None:
    completed_tags = {tag for runtime in state.beat_runtime.values() for tag in runtime.completed_tags}
    newly_completed = {tag for update in result.beat_updates for tag in update.completion_tags}
    operation_text = json.dumps([item.model_dump() for item in result.operations])
    visible = " ".join([result.narration, result.summary_delta or "", operation_text]).casefold()
    for revelation in state.compiled_story.protected_revelations:
        released = set(revelation.reveal_after) <= completed_tags | newly_completed
        if not released and revelation.summary.casefold() in visible:
            raise RuntimeFailure(
                "PROTECTED_REVELATION",
                f"protected revelation '{revelation.id}' leaked before release",
            )
