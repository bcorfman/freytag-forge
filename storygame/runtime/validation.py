"""Minimal local validator and clone-first atomic state commit."""

from __future__ import annotations

import copy
import json
from typing import Any

from storygame.authoring.causal_contracts import Consequence, InteractionFrame
from storygame.runtime.contracts import (
    ActionSegment,
    DialogueProposal,
    DocumentDisclosure,
    InteractionProposal,
    RuntimeFailure,
    SpeechSegment,
    StoryletRealization,
    TurnResult,
)
from storygame.runtime.facts import Fact
from storygame.runtime.narrative import RuntimeNarrativePackage, StoryletSelector
from storygame.runtime.state import RuntimeState


def validate_and_commit(
    state: RuntimeState,
    result: TurnResult,
    *,
    player_input: str = "",
) -> RuntimeState:
    candidate = copy.deepcopy(state)
    if result.interaction is not None:
        _validate_interaction(candidate, result.interaction, player_input)
    if result.dialogue is not None:
        _validate_dialogue(candidate, result.dialogue, player_input)
    _reject_opening_orientation_reuse(candidate, result)
    _reject_protected_leaks(candidate, result)
    if result.storylet_realization is not None:
        _apply_storylet_realization(candidate, result.storylet_realization)
    if result.interaction is not None and result.interaction.storylet_realization is not None:
        _apply_storylet_realization(candidate, result.interaction.storylet_realization)
    _apply_disclosures(candidate, result.disclosures)
    for operation in result.operations:
        _apply_operation(candidate, operation.kind, operation.path, operation.value)
    if result.dialogue is not None:
        for operation in result.dialogue.effects:
            _apply_operation(candidate, operation.kind, operation.path, operation.value)
    if result.interaction is not None:
        for effect in result.interaction.effects:
            operation = effect.operation
            _apply_operation(candidate, operation.kind, operation.path, operation.value)
        _apply_interaction_lifecycle(candidate, result.interaction)
    _apply_beat_updates(candidate, result)
    _apply_timed_events(candidate, candidate.turn_index + 1)
    return candidate


def _reject_opening_orientation_reuse(state: RuntimeState, result: TurnResult) -> None:
    interaction = result.interaction
    if interaction is None or (interaction.group_encounter_id is None and interaction.inspection_target_id is None):
        return
    opening = state.compiled_story.opening
    if opening is None:
        return
    orientation = {
        text.casefold().strip().rstrip(".!?")
        for text in (opening.scene, opening.player_context, opening.situation)
        if text
    }
    visible = [result.narration, *(segment.text for segment in interaction.segments)]
    if any(text.casefold().strip().rstrip(".!?") in orientation for text in visible):
        raise RuntimeFailure(
            "OPENING_ORIENTATION_REUSED",
            "group and inspection responses must advance the current fact-backed scene",
        )


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
    "subject_discovered",
    "evidence_discovered",
    "group_introduced",
    "met",
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


def _validate_interaction(state: RuntimeState, interaction: InteractionProposal, player_input: str) -> None:
    if interaction.inspection_target_id is not None:
        _validate_inspection(state, interaction)
        return
    package = state.narrative_package
    if package is None:
        raise RuntimeFailure("INTERACTION_PACKAGE_UNAVAILABLE", "this session has no reviewed interaction package")
    frame = next((item for item in package.interaction_frames if item.id == interaction.interaction_frame_id), None)
    if frame is None:
        raise RuntimeFailure(
            "UNKNOWN_INTERACTION_FRAME", f"unknown interaction frame '{interaction.interaction_frame_id}'"
        )
    _validate_interaction_participants(state, frame, interaction)
    _validate_interaction_initiation(state, package, frame, interaction, player_input)
    _validate_interaction_segments(state, frame, interaction, player_input)
    if (
        interaction.storylet_realization is not None
        and interaction.storylet_realization.storylet_id != frame.storylet_id
    ):
        raise RuntimeFailure("INTERACTION_STORYLET_MISMATCH", "interaction realization does not belong to its frame")
    if interaction.agency_mode is not None and interaction.agency_mode not in frame.agency_modes:
        raise RuntimeFailure("UNDECLARED_INTERACTION_AGENCY", "interaction uses an undeclared player response mode")
    if interaction.outcome == "complete" and (
        interaction.storylet_realization is None or not interaction.storylet_realization.completion_evidence
    ):
        raise RuntimeFailure("INTERACTION_COMPLETION_UNGROUNDED", "completion requires a reviewed storylet realization")


def _validate_interaction_participants(
    state: RuntimeState, frame: InteractionFrame, interaction: InteractionProposal
) -> None:
    expected = set(frame.participant_ids) | {"player"}
    proposed = set(interaction.participant_ids)
    if len(proposed) != len(interaction.participant_ids) or proposed != expected:
        raise RuntimeFailure("INTERACTION_PARTICIPANTS", "interaction participants do not match the reviewed frame")
    responder_ids = expected - {"player"}
    for participant_id in responder_ids:
        _validate_present_responder(state, participant_id)
    if state.world.location not in frame.location_ids:
        raise RuntimeFailure("INTERACTION_LOCATION", "interaction frame is not valid in the current location")
    _validate_group_encounter(state, interaction, responder_ids)
    _validate_responder_profiles(state, responder_ids)


def _validate_present_responder(state: RuntimeState, participant_id: str) -> None:
    if not state.facts.has("present", participant_id, state.world.location):
        raise RuntimeFailure("UNAVAILABLE_SPEAKER", f"participant '{participant_id}' is not on scene")
    if not state.facts.has("npc_availability", participant_id, value="present"):
        raise RuntimeFailure("UNAVAILABLE_SPEAKER", f"participant '{participant_id}' is unavailable")


def _validate_group_encounter(state: RuntimeState, interaction: InteractionProposal, responder_ids: set[str]) -> None:
    if len(responder_ids) == 1 and interaction.group_encounter_id is None:
        return
    if len(responder_ids) > 1 and interaction.group_encounter_id is None:
        raise RuntimeFailure(
            "GROUP_ENCOUNTER_REQUIRED", "multiple responders require a declared current group encounter"
        )
    package = state.narrative_package
    if package is None:
        raise RuntimeFailure("INTERACTION_PACKAGE_UNAVAILABLE", "this session has no reviewed interaction package")
    encounter = next((item for item in package.group_encounters if item.id == interaction.group_encounter_id), None)
    if encounter is None:
        raise RuntimeFailure("UNKNOWN_GROUP_ENCOUNTER", "interaction names no declared group encounter")
    if not state.facts.has("group_at", encounter.id, state.world.location):
        raise RuntimeFailure("GROUP_NOT_PRESENT", "the declared group is not in the current scene")
    if set(encounter.participant_ids) != responder_ids:
        raise RuntimeFailure("GROUP_MEMBERSHIP_MISMATCH", "interaction responders do not match the declared group")
    if set(encounter.introduction_truth_ids) & package.protected_truth_ids:
        raise RuntimeFailure("PROTECTED_GROUP_INTRODUCTION", "group introduction cannot disclose protected truth")
    for participant_id in encounter.participant_ids:
        if not state.facts.has("group_member", encounter.id, participant_id):
            raise RuntimeFailure("GROUP_MEMBERSHIP_MISMATCH", "group membership lacks a canonical fact")


def _validate_responder_profiles(state: RuntimeState, responder_ids: set[str]) -> None:
    package = state.narrative_package
    if package is None:
        raise RuntimeFailure("INTERACTION_PACKAGE_UNAVAILABLE", "this session has no reviewed interaction package")
    profiled = {profile.participant_id for profile in package.npc_performance_profiles}
    for participant_id in responder_ids:
        if participant_id not in profiled:
            raise RuntimeFailure(
                "NPC_PROFILE_UNAVAILABLE", f"participant '{participant_id}' has no performance profile"
            )


def _validate_interaction_initiation(
    state: RuntimeState,
    package: RuntimeNarrativePackage,
    frame: InteractionFrame,
    interaction: InteractionProposal,
    player_input: str,
) -> None:
    active = state.facts.has("interaction_active", frame.id, value="true")
    addressed = interaction.addressed_participant_id or frame.initiator_id
    responders = set(frame.participant_ids)
    if addressed not in responders:
        raise RuntimeFailure("INVALID_INTERACTION_TARGET", "the addressed participant is not a declared responder")
    if (
        interaction.initiation in {"continuation", "player_initiated"}
        and len(responders) > 1
        and interaction.addressed_participant_id is None
    ):
        raise RuntimeFailure("GROUP_TARGET_REQUIRED", "a player addressing a group must name one responder")
    if interaction.initiation == "continuation":
        if not active:
            raise RuntimeFailure("INACTIVE_INTERACTION", "interaction continuation requires an active frame")
        if not _mentions_dialogue_target(state, addressed, player_input):
            raise RuntimeFailure("TARGET_NOT_ADDRESSED", f"player did not address '{addressed}'")
        return
    if active:
        raise RuntimeFailure("INVALID_INTERACTION_INITIATION", "an active interaction must continue through its frame")
    if interaction.initiation == "npc_initiated" and frame.initiation not in {"npc_initiated", "either"}:
        raise RuntimeFailure("INVALID_INTERACTION_INITIATION", "frame does not permit NPC initiation")
    if interaction.initiation == "player_initiated":
        if frame.initiation not in {"player_initiated", "either"}:
            raise RuntimeFailure("INVALID_INTERACTION_INITIATION", "frame does not permit player initiation")
        if not _mentions_dialogue_target(state, addressed, player_input):
            raise RuntimeFailure("TARGET_NOT_ADDRESSED", f"player did not address '{addressed}'")
    eligible = StoryletSelector(package, state.facts).select(
        active_beat_ids=tuple(beat.id for beat in state.active_beats),
        location_id=state.world.location,
        limit=len(package.storylets),
    )
    if not any(storylet.id == frame.storylet_id for storylet in eligible):
        raise RuntimeFailure("INELIGIBLE_INTERACTION", "interaction frame has no eligible reviewed storylet")


def _validate_interaction_segments(
    state: RuntimeState,
    frame: InteractionFrame,
    interaction: InteractionProposal,
    player_input: str,
) -> None:
    speakers: set[str] = set()
    for segment in interaction.segments:
        if isinstance(segment, SpeechSegment):
            _validate_speech_segment(state, frame, interaction, segment, player_input)
            speakers.add(segment.speaker_id)
        elif isinstance(segment, ActionSegment):
            _validate_action_segment(state, frame, interaction, segment)
        else:
            raise RuntimeFailure("INVALID_INTERACTION_SEGMENT", "interaction segment is not typed")
    if interaction.addressed_participant_id is not None and interaction.addressed_participant_id not in speakers:
        raise RuntimeFailure(
            "ADDRESSED_PARTICIPANT_SILENT", "the addressed participant must supply an attributed reply"
        )


def _validate_speech_segment(
    state: RuntimeState,
    frame: InteractionFrame,
    interaction: InteractionProposal,
    segment: SpeechSegment,
    player_input: str,
) -> None:
    responder_ids = set(frame.participant_ids)
    if segment.speaker_id not in responder_ids or segment.speaker_id not in interaction.participant_ids:
        raise RuntimeFailure("WRONG_SPEAKER", "speech must be attributed to a declared present responder")
    if not set(segment.addressee_ids) <= set(interaction.participant_ids) or "player" not in segment.addressee_ids:
        raise RuntimeFailure("INVALID_ADDRESSEE", "speech must address a declared player participant")
    for fact_id in segment.used_fact_ids:
        if not state.facts.has("knows", segment.speaker_id, fact_id):
            raise RuntimeFailure("SPEAKER_LACKS_KNOWLEDGE", f"speaker lacks permitted fact '{fact_id}'")
    _reject_parroting_or_narrator_substitution(state, segment.speaker_id, segment.text, player_input)


def _validate_action_segment(
    state: RuntimeState,
    frame: InteractionFrame,
    interaction: InteractionProposal,
    segment: ActionSegment,
) -> None:
    responder_ids = set(frame.participant_ids)
    if segment.actor_id not in responder_ids or segment.actor_id not in interaction.participant_ids:
        raise RuntimeFailure("WRONG_ACTOR", "action must be attributed to a declared present responder")
    _validate_present_responder(state, segment.actor_id)
    if segment.grounding == "material" and not segment.effect_refs:
        raise RuntimeFailure("UNGROUNDED_MATERIAL_ACTION", "material action requires committed effects")


def _validate_inspection(state: RuntimeState, interaction: InteractionProposal) -> None:
    target_id = interaction.inspection_target_id
    if target_id is None:
        raise RuntimeFailure("UNKNOWN_INSPECTION_TARGET", "inspection lacks a declared target")
    subject = _visible_scene_subject(state, target_id)
    item_visible = _visible_item(state, target_id)
    if subject is None and not item_visible:
        raise RuntimeFailure("UNKNOWN_INSPECTION_TARGET", "inspection target is not currently visible")
    if interaction.participant_ids != ("player",):
        raise RuntimeFailure("INSPECTION_PARTICIPANTS", "inspection may name only the player as a participant")
    _validate_inspection_segments(state, interaction, target_id)
    _validate_inspection_effects(state, interaction, target_id, subject is not None)


def _visible_scene_subject(state: RuntimeState, target_id: str) -> object | None:
    package = state.narrative_package
    if package is None:
        return None
    subject = next((item for item in package.scene_subjects if item.id == target_id), None)
    if subject is None or not subject.inspectable:
        return None
    if not state.facts.has("at", subject.id, state.world.location):
        return None
    return subject


def _visible_item(state: RuntimeState, target_id: str) -> bool:
    item = state.world.items.get(target_id)
    if item is None:
        return False
    holder = item.get("holder")
    return (
        holder == "player"
        or holder == f"location:{state.world.location}"
        or (isinstance(holder, str) and holder.startswith("npc:") and _holder_is_available(state, holder))
    )


def _validate_inspection_segments(state: RuntimeState, interaction: InteractionProposal, target_id: str) -> None:
    for segment in interaction.segments:
        if isinstance(segment, ActionSegment):
            if segment.actor_id != "player":
                raise RuntimeFailure("WRONG_INSPECTION_ACTOR", "inspection actions must be attributed to the player")
        elif isinstance(segment, SpeechSegment):
            if segment.speaker_id != "player" or set(segment.addressee_ids) != {target_id}:
                raise RuntimeFailure("INVALID_INSPECTION_SPEECH", "inspection speech must address the declared target")
            for fact_id in segment.used_fact_ids:
                if not state.facts.has("knows", "player", fact_id):
                    raise RuntimeFailure("PLAYER_LACKS_KNOWLEDGE", f"player lacks fact '{fact_id}'")
        else:
            raise RuntimeFailure("INVALID_INTERACTION_SEGMENT", "inspection segment is not typed")


def _validate_inspection_effects(
    state: RuntimeState, interaction: InteractionProposal, target_id: str, is_scene_subject: bool
) -> None:
    referenced_effect_ids = {
        effect_id
        for segment in interaction.segments
        if isinstance(segment, ActionSegment)
        for effect_id in segment.effect_refs
    }
    if referenced_effect_ids != {effect.id for effect in interaction.effects}:
        raise RuntimeFailure("UNDECLARED_INSPECTION_EFFECT", "inspection effects must ground one material action")
    if not interaction.effects:
        return
    if not is_scene_subject:
        raise RuntimeFailure("UNDECLARED_INSPECTION_EFFECT", "only declared scene subjects can reveal evidence")
    package = state.narrative_package
    if package is None:
        raise RuntimeFailure("INTERACTION_PACKAGE_UNAVAILABLE", "this session has no reviewed interaction package")
    evidence_by_id = {item.id: item for item in package.evidence_realizations}
    for effect in interaction.effects:
        operation = effect.operation
        if operation.kind != "add" or operation.path != "facts":
            raise RuntimeFailure("UNDECLARED_INSPECTION_EFFECT", "inspection may commit only declared discovery facts")
        try:
            fact = Fact.model_validate(operation.value)
        except (TypeError, ValueError) as exc:
            raise RuntimeFailure("INVALID_INSPECTION_DISCOVERY", "inspection discovery is not a typed fact") from exc
        if fact.value != "true":
            raise RuntimeFailure("INVALID_INSPECTION_DISCOVERY", "inspection discoveries must assert true")
        if fact.predicate == "subject_discovered" and fact.subject == target_id:
            continue
        evidence = evidence_by_id.get(fact.subject)
        if (
            fact.predicate != "evidence_discovered"
            or evidence is None
            or evidence.location_id != state.world.location
            or evidence.scene_subject_id != target_id
        ):
            raise RuntimeFailure("INVALID_INSPECTION_DISCOVERY", "inspection cannot discover absent evidence")


def _apply_interaction_lifecycle(state: RuntimeState, interaction: InteractionProposal) -> None:
    if interaction.inspection_target_id is not None:
        return
    package = state.narrative_package
    if package is None:
        raise RuntimeFailure("INTERACTION_PACKAGE_UNAVAILABLE", "this session has no reviewed interaction package")
    frame = next(item for item in package.interaction_frames if item.id == interaction.interaction_frame_id)
    state.facts.assert_fact(Fact(predicate="interaction_active", subject=frame.id, value="true"))
    state.facts.assert_fact(Fact(predicate="interaction_recently_used", subject=frame.id, value="true"))
    if interaction.group_encounter_id is not None:
        encounter = next(item for item in package.group_encounters if item.id == interaction.group_encounter_id)
        state.facts.assert_fact(Fact(predicate="group_introduced", subject=encounter.id, value="true"))
        for participant_id in encounter.participant_ids:
            state.facts.assert_fact(Fact(predicate="met", subject="player", object=participant_id))
        for truth_id in encounter.introduction_truth_ids:
            state.facts.assert_fact(Fact(predicate="knows", subject="player", object=truth_id))
    if interaction.outcome == "complete":
        state.facts.assert_fact(Fact(predicate="interaction_completed", subject=frame.id, value="true"))
    if interaction.outcome == "abort":
        state.facts.assert_fact(Fact(predicate="interaction_aborted", subject=frame.id, value="true"))
        for next_frame_id in frame.failure_forward_frame_ids:
            state.facts.assert_fact(Fact(predicate="interaction_active", subject=next_frame_id, value="true"))


def _reject_parroting_or_narrator_substitution(
    state: RuntimeState, speaker_id: str, text: str, player_input: str
) -> None:
    normalized_text = " ".join(text.casefold().split()).strip(" .!?")
    normalized_input = " ".join(player_input.casefold().split()).strip(" .!?")
    if normalized_input and normalized_text == normalized_input:
        raise RuntimeFailure("DIALOGUE_PROMPT_PARROTING", "dialogue repeats the player's prompt")
    names = {part for part in speaker_id.casefold().split("_") if len(part) > 2}
    opening = state.compiled_story.opening
    if opening is not None:
        names.update(contact.name.casefold() for contact in opening.contacts if contact.id == speaker_id)
    if any(normalized_text.startswith(f"{name} says") for name in names):
        raise RuntimeFailure("DIALOGUE_NARRATOR_SUBSTITUTION", "dialogue must be spoken by the addressed NPC")


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
    _reject_parroting_or_narrator_substitution(state, dialogue.speaker_id, dialogue.dialogue, player_input)


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
    interaction_text = ""
    interaction_effects = ""
    if result.interaction is not None:
        interaction_text = " ".join(segment.text for segment in result.interaction.segments)
        interaction_effects = json.dumps([item.model_dump() for item in result.interaction.effects])
    visible = " ".join(
        [
            result.narration,
            dialogue_text,
            interaction_text,
            result.summary_delta or "",
            operation_text,
            interaction_effects,
        ]
    ).casefold()
    for revelation in state.compiled_story.protected_revelations:
        released = set(revelation.reveal_after) <= completed_tags | newly_completed
        if not released and revelation.summary.casefold() in visible:
            raise RuntimeFailure(
                "PROTECTED_REVELATION",
                f"protected revelation '{revelation.id}' leaked before release",
            )
