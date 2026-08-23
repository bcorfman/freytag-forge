"""Minimal local validator and clone-first atomic state commit."""

from __future__ import annotations

import copy
import json
from typing import Any

from storygame.runtime.contracts import DocumentDisclosure, RuntimeFailure, TurnResult
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState


def validate_and_commit(state: RuntimeState, result: TurnResult) -> RuntimeState:
    candidate = copy.deepcopy(state)
    _reject_protected_leaks(candidate, result)
    _apply_disclosures(candidate, result.disclosures)
    for operation in result.operations:
        _apply_operation(candidate, operation.kind, operation.path, operation.value)
    _apply_beat_updates(candidate, result)
    return candidate


def _apply_operation(state: RuntimeState, kind: str, path: str, value: Any) -> None:
    if path == "facts" and kind in {"add", "remove"}:
        _apply_fact_operation(state, kind, value)
        return
    if path == "world.location" and kind == "set" and isinstance(value, str) and value:
        state.world.location = value
        return
    if path == "world.flags":
        if kind in {"add", "remove"} and isinstance(value, str):
            (state.world.flags.add if kind == "add" else state.world.flags.discard)(value)
            return
        if kind == "set" and isinstance(value, list) and all(isinstance(flag, str) and flag for flag in value):
            state.world.flags = set(value)
            return
    if path.startswith("world.attributes.") and kind == "set":
        state.world.attributes[path.removeprefix("world.attributes.")] = value
        return
    if path.startswith("world.items.") and path.endswith(".holder") and kind == "set" and isinstance(value, str):
        item_id = path.split(".")[2]
        item = state.world.items.get(item_id)
        if item is None:
            raise RuntimeFailure("UNKNOWN_ITEM", f"item '{item_id}' is not declared")
        previous = item.get("holder")
        if value == "player" and isinstance(previous, str) and not _holder_is_available(state, previous):
            raise RuntimeFailure("ITEM_UNAVAILABLE", f"item '{item_id}' is not available in the current scene")
        if isinstance(previous, str) and previous != value:
            state.facts.retract_fact(Fact(predicate="custody", subject=item_id, object=previous))
        item["holder"] = value
        state.facts.assert_fact(Fact(predicate="custody", subject=item_id, object=value))
        if value == "player":
            state.facts.assert_fact(Fact(predicate="possession", subject="player", object=item_id))
            _sync_fact_view(state, Fact(predicate="possession", subject="player", object=item_id), "add")
        elif isinstance(previous, str):
            possession = Fact(predicate="possession", subject="player", object=item_id)
            state.facts.retract_fact(possession)
            _sync_fact_view(state, possession, "remove")
        return
    raise RuntimeFailure("UNKNOWN_STATE_PATH", f"operation '{kind}' cannot modify '{path}'")


def _holder_is_available(state: RuntimeState, holder: str) -> bool:
    if holder == "player":
        return True
    if holder.startswith("location:"):
        return holder.removeprefix("location:") == state.world.location
    if holder.startswith("npc:"):
        npc_id = holder.removeprefix("npc:")
        return state.facts.has("at", npc_id, state.world.location) or state.facts.has(
            "present", npc_id, state.world.location
        )
    return False


_FACT_FAMILIES = {
    "identity",
    "role",
    "at",
    "present",
    "custody",
    "possession",
    "knows",
    "unknown",
    "discovered_clue",
    "discovered_lead",
    "active_goal",
    "task",
    "scene_objective",
    "relationship",
    "npc_available",
    "item_affordance",
    "flag",
}


def _apply_fact_operation(state: RuntimeState, kind: str, value: Any) -> None:
    try:
        fact = Fact.model_validate(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeFailure("INVALID_FACT", f"fact operation is not a valid typed fact: {exc}") from exc
    if fact.predicate not in _FACT_FAMILIES:
        raise RuntimeFailure("UNKNOWN_FACT_FAMILY", f"fact family '{fact.predicate}' is not writable")
    if fact.predicate in {"custody", "possession", "at", "present"} and fact.object is None:
        raise RuntimeFailure("INVALID_FACT", f"fact family '{fact.predicate}' requires an object")
    if fact.predicate == "custody":
        if fact.subject not in state.world.items:
            raise RuntimeFailure("UNKNOWN_ITEM", f"item '{fact.subject}' is not declared")
        existing = state.facts.matching("custody", fact.subject)
        if kind == "add" and any(item.object != fact.object for item in existing):
            raise RuntimeFailure("UNIQUE_CUSTODY_CONFLICT", f"item '{fact.subject}' already has a different holder")
    target = state.facts.assert_fact if kind == "add" else state.facts.retract_fact
    target(fact)
    _sync_fact_view(state, fact, kind)


def _apply_disclosures(state: RuntimeState, disclosures: tuple[DocumentDisclosure, ...]) -> None:
    for disclosure in disclosures:
        item = state.world.items.get(disclosure.item_id)
        readable = item.get("readable") if item is not None else None
        if not isinstance(readable, dict):
            raise RuntimeFailure("DOCUMENT_NOT_READABLE", f"item '{disclosure.item_id}' is not a readable document")
        permitted = readable.get("npc_disclosures", {}).get(disclosure.speaker_id, ())
        if disclosure.fact_id not in permitted:
            raise RuntimeFailure(
                "WRONG_SPEAKER_DISCLOSURE",
                f"speaker '{disclosure.speaker_id}' cannot disclose '{disclosure.fact_id}' from '{disclosure.item_id}'",
            )
        if not state.facts.has("at", disclosure.speaker_id, state.world.location) and not state.facts.has(
            "present", disclosure.speaker_id, state.world.location
        ):
            raise RuntimeFailure("UNAVAILABLE_SPEAKER", f"speaker '{disclosure.speaker_id}' is not on scene")
        if not state.facts.has("knows", disclosure.speaker_id, disclosure.fact_id):
            raise RuntimeFailure("SPEAKER_LACKS_KNOWLEDGE", f"speaker '{disclosure.speaker_id}' does not know the fact")
        if state.facts.has("knows", "player", disclosure.fact_id):
            raise RuntimeFailure("FACT_ALREADY_KNOWN", f"player already knows '{disclosure.fact_id}'")
        _apply_fact_operation(
            state,
            "add",
            Fact(predicate="knows", subject="player", object=disclosure.fact_id).model_dump(mode="json"),
        )


def _sync_fact_view(state: RuntimeState, fact: Fact, kind: str) -> None:
    if fact.predicate == "custody" and fact.subject in state.world.items:
        if kind == "add":
            state.world.items[fact.subject]["holder"] = fact.object
        elif state.world.items[fact.subject].get("holder") == fact.object:
            state.world.items[fact.subject].pop("holder", None)
    elif fact.predicate == "possession" and fact.subject == "player" and fact.object:
        possessed = set(state.world.attributes.get("inventory", []))
        (possessed.add if kind == "add" else possessed.discard)(fact.object)
        state.world.attributes["inventory"] = sorted(possessed)
    elif fact.predicate == "at" and fact.subject == "player" and fact.object and kind == "add":
        state.world.location = fact.object
    elif fact.predicate == "flag" and fact.object:
        (state.world.flags.add if kind == "add" else state.world.flags.discard)(fact.object)
    elif fact.predicate in {"discovered_clue", "discovered_lead"} and fact.object:
        key = "discovered_clues" if fact.predicate == "discovered_clue" else "discovered_leads"
        values = set(state.world.attributes.get(key, []))
        (values.add if kind == "add" else values.discard)(fact.object)
        state.world.attributes[key] = sorted(values)
    elif fact.predicate == "knows" and fact.subject == "player" and fact.object:
        unknown = set(state.world.attributes.get("unknown_facts", []))
        (unknown.discard if kind == "add" else unknown.add)(fact.object)
        state.world.attributes["unknown_facts"] = sorted(unknown)


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
            raise RuntimeFailure(
                "UNKNOWN_COMPLETION_TAG",
                f"beat '{beat.id}' received an undeclared completion tag; allowed tags: {sorted(allowed)}",
            )
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
