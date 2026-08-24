"""Minimal local validator and clone-first atomic state commit."""

from __future__ import annotations

import copy
import json
from typing import Any

from storygame.authoring.causal_contracts import Consequence
from storygame.runtime.contracts import (
    DialogueProposal,
    DocumentDisclosure,
    RuntimeFailure,
    StoryletRealization,
    TurnResult,
)
from storygame.runtime.facts import Fact
from storygame.runtime.narrative import StoryletSelector
from storygame.runtime.state import RuntimeState


def validate_and_commit(
    state: RuntimeState,
    result: TurnResult,
    *,
    player_input: str = "",
) -> RuntimeState:
    candidate = copy.deepcopy(state)
    if result.dialogue is not None:
        _validate_dialogue(candidate, result.dialogue, player_input)
    _reject_protected_leaks(candidate, result)
    if result.storylet_realization is not None:
        _apply_storylet_realization(candidate, result.storylet_realization)
    _apply_disclosures(candidate, result.disclosures)
    for operation in result.operations:
        _apply_operation(candidate, operation.kind, operation.path, operation.value)
    if result.dialogue is not None:
        for operation in result.dialogue.effects:
            _apply_operation(candidate, operation.kind, operation.path, operation.value)
    _apply_beat_updates(candidate, result)
    _apply_timed_events(candidate, candidate.turn_index + 1)
    return candidate


def _apply_storylet_realization(state: RuntimeState, realization: StoryletRealization) -> None:
    package = state.narrative_package
    if package is None:
        raise RuntimeFailure("STORYLET_PACKAGE_UNAVAILABLE", "this session has no reviewed storylet package")
    storylet = next((item for item in package.storylets if item.id == realization.storylet_id), None)
    if storylet is None:
        raise RuntimeFailure("UNKNOWN_STORYLET", f"unknown storylet '{realization.storylet_id}'")
    eligible = StoryletSelector(package, state.facts).select(
        active_beat_ids=tuple(beat.id for beat in state.active_beats),
        location_id=state.world.location,
        limit=len(package.storylets),
    )
    if storylet not in eligible:
        raise RuntimeFailure("INELIGIBLE_STORYLET", f"storylet '{storylet.id}' is ineligible at this fact snapshot")
    if realization.realization_mode not in storylet.realization_modes:
        raise RuntimeFailure(
            "INVALID_STORYLET_MODE", f"storylet '{storylet.id}' does not allow '{realization.realization_mode}'"
        )
    duplicate_consequences = len(set(realization.consequence_ids)) != len(realization.consequence_ids)
    if duplicate_consequences or not set(realization.consequence_ids) <= set(storylet.consequence_ids):
        raise RuntimeFailure(
            "UNKNOWN_STORYLET_CONSEQUENCE", f"storylet '{storylet.id}' received an undeclared consequence"
        )
    if realization.completion_evidence and realization.abort_evidence:
        raise RuntimeFailure(
            "STORYLET_OUTCOME_CONFLICT", "a storylet cannot complete and abort in the same realization"
        )
    _apply_storylet_consequences(state, package.consequences, realization.consequence_ids)
    _mark_storylet(state, "storylet_active", storylet.id)
    _mark_storylet(state, "storylet_discovered", storylet.id)
    _mark_storylet(state, "storylet_recently_used", storylet.id)
    if realization.completion_evidence:
        if set(realization.completion_evidence) != {storylet.completion_truth_id} or not state.facts.has(
            "knows", "player", storylet.completion_truth_id
        ):
            raise RuntimeFailure(
                "INVALID_STORYLET_COMPLETION", f"storylet '{storylet.id}' lacks declared completion evidence"
            )
        _mark_storylet(state, "storylet_completed", storylet.id)
    if realization.abort_evidence:
        if not set(realization.abort_evidence) <= set(storylet.abort_truth_ids):
            raise RuntimeFailure("INVALID_STORYLET_ABORT", f"storylet '{storylet.id}' lacks declared abort evidence")
        _mark_storylet(state, "storylet_aborted", storylet.id)
        for target_id in storylet.failure_forward_storylet_ids:
            _mark_storylet(state, "storylet_discovered", target_id)


def _apply_storylet_consequences(
    state: RuntimeState, consequences: tuple[Consequence, ...], ids: tuple[str, ...]
) -> None:
    templates = {item.id: item for item in consequences}
    for consequence_id in ids:
        template = templates.get(consequence_id)
        if template is None:
            raise RuntimeFailure("UNKNOWN_STORYLET_CONSEQUENCE", f"unknown consequence '{consequence_id}'")
        for truth_id in template.assert_truth_ids:
            state.facts.assert_fact(Fact(predicate="knows", subject="player", object=truth_id))
        for truth_id in template.retract_truth_ids:
            state.facts.retract_fact(Fact(predicate="knows", subject="player", object=truth_id))


def _mark_storylet(state: RuntimeState, predicate: str, storylet_id: str) -> None:
    state.facts.assert_fact(Fact(predicate=predicate, subject=storylet_id, value="true"))


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
    "goal",
    "task",
    "clue",
    "scene_objective",
    "current_scene",
    "scene_pressure",
    "dramatic_question",
    "relationship",
    "npc_available",
    "item_affordance",
    "flag",
    "event_fired",
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


def _validate_dialogue(state: RuntimeState, dialogue: object, player_input: str) -> None:
    if not isinstance(dialogue, DialogueProposal):
        raise RuntimeFailure("INVALID_DIALOGUE", "dialogue proposal is not typed")
    target_present = state.facts.has("at", dialogue.target_id, state.world.location) or state.facts.has(
        "present", dialogue.target_id, state.world.location
    )
    if not target_present:
        raise RuntimeFailure("UNAVAILABLE_SPEAKER", f"target '{dialogue.target_id}' is not on scene")
    if dialogue.speaker_id != dialogue.target_id:
        raise RuntimeFailure("WRONG_SPEAKER", "dialogue speaker must match the addressed target")
    if not _mentions_dialogue_target(state, dialogue.target_id, player_input):
        raise RuntimeFailure("TARGET_NOT_ADDRESSED", f"player did not address '{dialogue.target_id}'")
    for fact_id in dialogue.permitted_context:
        if not state.facts.has("knows", dialogue.speaker_id, fact_id):
            raise RuntimeFailure(
                "SPEAKER_LACKS_KNOWLEDGE",
                f"speaker '{dialogue.speaker_id}' lacks permitted fact '{fact_id}'",
            )
    normalized_dialogue = " ".join(dialogue.dialogue.casefold().split()).strip(" .!?")
    normalized_input = " ".join(player_input.casefold().split()).strip(" .!?")
    if normalized_dialogue == normalized_input:
        raise RuntimeFailure("DIALOGUE_PROMPT_PARROTING", "dialogue repeats the player's prompt")
    names = {part for part in dialogue.speaker_id.casefold().split("_") if len(part) > 2}
    opening = state.compiled_story.opening
    if opening is not None:
        names.update(contact.name.casefold() for contact in opening.contacts if contact.id == dialogue.speaker_id)
    if any(normalized_dialogue.startswith(f"{name} says") for name in names):
        raise RuntimeFailure("DIALOGUE_NARRATOR_SUBSTITUTION", "dialogue must be spoken by the addressed NPC")


def _mentions_dialogue_target(state: RuntimeState, target_id: str, player_input: str) -> bool:
    request = player_input.casefold()
    aliases = {target_id.casefold().replace("_", " ")}
    aliases.update(part for part in target_id.casefold().split("_") if len(part) > 2)
    opening = state.compiled_story.opening
    if opening is not None:
        aliases.update(contact.name.casefold() for contact in opening.contacts if contact.id == target_id)
    return any(alias and alias in request for alias in aliases)


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


def _apply_timed_events(state: RuntimeState, turn_index: int) -> None:
    """Commit each due declaration once, before the turn can be rendered."""

    for event in state.compiled_story.timed_events:
        if event.after_turn > turn_index or state.facts.matching("event_fired", event.id):
            continue
        for declaration in event.consequence_facts:
            _apply_fact_operation(state, "add", declaration.model_dump(mode="json"))
        _apply_fact_operation(
            state,
            "add",
            Fact(predicate="event_fired", subject=event.id, value=str(turn_index)).model_dump(mode="json"),
        )
        if event.pressure_change:
            current = next(
                (int(fact.value) for fact in state.facts.matching("scene_pressure", "scene") if fact.value),
                0,
            )
            updated = max(0, min(100, current + event.pressure_change))
            for fact in state.facts.matching("scene_pressure", "scene"):
                state.facts.retract_fact(fact)
            _apply_fact_operation(
                state,
                "add",
                Fact(predicate="scene_pressure", subject="scene", value=str(updated)).model_dump(mode="json"),
            )


def _reject_protected_leaks(state: RuntimeState, result: TurnResult) -> None:
    completed_tags = {tag for runtime in state.beat_runtime.values() for tag in runtime.completed_tags}
    newly_completed = {tag for update in result.beat_updates for tag in update.completion_tags}
    operation_text = json.dumps([item.model_dump() for item in result.operations])
    dialogue_text = result.dialogue.dialogue if result.dialogue is not None else ""
    visible = " ".join([result.narration, dialogue_text, result.summary_delta or "", operation_text]).casefold()
    for revelation in state.compiled_story.protected_revelations:
        released = set(revelation.reveal_after) <= completed_tags | newly_completed
        if not released and revelation.summary.casefold() in visible:
            raise RuntimeFailure(
                "PROTECTED_REVELATION",
                f"protected revelation '{revelation.id}' leaked before release",
            )
