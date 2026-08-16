# ruff: noqa: E501

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from random import Random
from typing import Any, Protocol, TextIO

from rich.console import Console

from storygame.engine.facts import apply_fact_ops
from storygame.engine.freeform import (
    _HIDDEN_FREEFORM_MESSAGE_KEYS,
    DEFAULT_FREEFORM_ADAPTER,
    FreeformProposalAdapter,
    LlmFreeformProposalAdapter,
    RuleBasedFreeformProposalAdapter,
    _normalized_dialog_speaker_id,
    _normalized_movement_action_payload,
    _semantic_exit_direction,
    _takeable_item_for_input,
    addressed_visible_npc_id,
    bind_direct_npc_conversation_target,
    is_player_statement_echo,
    resolve_freeform_roleplay_with_proposals,
)
from storygame.engine.impact import (
    ImpactAssessment,
    assess_player_command,
    replan_scope_for_assessment,
    requires_high_impact_confirmation,
)
from storygame.engine.interfaces import parse_action_proposal
from storygame.engine.parser import Action, ActionKind, parse_control_command
from storygame.engine.presentation import story_status_lines
from storygame.engine.state import Event, GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import CloudflareWorkersAIAdapter, Narrator
from storygame.llm.coherence import CoherenceTelemetry
from storygame.llm.context import build_narration_context
from storygame.llm.contracts import JudgeDecision, NumericDelta
from storygame.llm.opening_coherence import player_facing_presentation_issues
from storygame.llm.output_editor import OutputEditor, build_output_editor
from storygame.llm.story_director import StoryDirector
from storygame.memory import MAX_MEMORY_NOTES, MemoryStore, SqliteVectorMemory, normalize_tag
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.plot.freytag import get_phase
from storygame.test_metrics import record


def _opening_story_editor(paragraphs: list[str]) -> list[str]:
    forbidden = (
        "move the story toward resolution",
        "where you are:",
        "cast:",
    )
    cleaned: list[str] = []
    for paragraph in paragraphs:
        normalized = " ".join(paragraph.split())
        normalized = re.sub(r"\bneutral\s+\w+\s+scene\b", "", normalized, flags=re.IGNORECASE)
        for fragment in forbidden:
            normalized = normalized.replace(fragment, "")
            normalized = normalized.replace(fragment.title(), "")
        normalized = normalized.strip(" ,")
        if normalized.lower().endswith("tasked with."):
            normalized = normalized[: -len("tasked with.")].rstrip(" ,.;")
            normalized = f"{normalized} and forced to take one final case."
        cleaned.append(normalized)
    return [paragraph for paragraph in cleaned if paragraph]


def _joined_with_and(values: tuple[str, ...] | list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _introduced_npc_ids(state: GameState) -> tuple[str, ...]:
    introduced = state.world_package.setdefault("introduced_npcs", [])
    return tuple(str(npc_id) for npc_id in introduced)


def _remember_npc_introductions(state: GameState, npc_ids: tuple[str, ...]) -> None:
    introduced = list(_introduced_npc_ids(state))
    changed = False
    for npc_id in npc_ids:
        if npc_id not in introduced:
            introduced.append(npc_id)
            changed = True
    if changed:
        state.world_package["introduced_npcs"] = introduced


def remember_opening_introductions(state: GameState, paragraphs: list[str]) -> None:
    opening_text = " ".join(paragraphs).lower()
    introduced = tuple(
        npc_id
        for npc_id, npc in state.world.npcs.items()
        if npc.name.strip() and npc.name.strip().lower() in opening_text
    )
    _remember_npc_introductions(state, introduced)


def filter_opening_room_repetition(state: GameState, paragraphs: list[str]) -> list[str]:
    room = state.world.rooms[state.player.location]
    room_text = room.description
    room_words = set(re.findall(r"[a-z]{3,}", room_text.lower()))
    filtered: list[str] = []
    for paragraph in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
        kept = []
        for sentence in sentences:
            words = set(re.findall(r"[a-z]{3,}", sentence.lower()))
            if len(words) < 4 or len(words.intersection(room_words)) * 2 <= len(words):
                kept.append(sentence)
        if kept:
            filtered.append(" ".join(kept))
    return filtered


def _setup_phase_lines(state: GameState, story_director: StoryDirector | None = None) -> list[str]:
    director = StoryDirector("cloudflare") if story_director is None else story_director
    opening = filter_opening_room_repetition(state, director.compose_opening(state))
    remember_opening_introductions(state, opening)
    return opening


def _with_paragraph_spacing(lines: list[str]) -> list[str]:
    if len(lines) <= 1:
        return list(lines)
    spaced: list[str] = []
    for index, line in enumerate(lines):
        spaced.append(line)
        if index < len(lines) - 1:
            spaced.append("")
    return spaced


_PROCEED_WORDS = {"proceed", "confirm", "yes", "y"}
_CANCEL_WORDS = {"cancel", "abort", "no", "n"}


def _clear_pending_high_impact(state: GameState) -> None:
    state.pending_high_impact_command = ""
    state.pending_high_impact_assessment = {}


def _impact_assessment_from_mapping(payload: dict[str, Any]) -> ImpactAssessment:
    dimensions_payload = payload.get("dimensions", {})
    return {
        "score": float(payload.get("score", 0.0)),
        "impact_class": str(payload.get("impact_class", "low")),
        "dimensions": {str(key): float(value) for key, value in dimensions_payload.items()},
        "reasons": [str(reason) for reason in payload.get("reasons", ())],
        "consequences": [str(consequence) for consequence in payload.get("consequences", ())],
    }


def _high_impact_warning_lines(assessment: ImpactAssessment) -> list[str]:
    impact_class = str(assessment.get("impact_class", "high")).upper()
    consequences = [str(item).strip() for item in assessment.get("consequences", []) if str(item).strip()]
    lines = [
        f"Goal-breaking action detected ({impact_class}). This would rupture the current story goals, NPC behavior, and event timing.",
    ]
    lines.extend(consequences[:2])
    lines.append("Type PROCEED to continue or CANCEL to abort.")
    return lines


def _record_major_disruption(
    state: GameState,
    events: list[Event],
    raw_command: str,
    assessment: ImpactAssessment,
) -> None:
    replan_scope = replan_scope_for_assessment(assessment)
    apply_fact_ops(
        state,
        [
            {"op": "assert", "fact": ("flag", "player", "story_replan_required")},
            {"op": "assert", "fact": ("flag", "player", "story_bounds_overridden")},
        ],
    )
    state.world_package["story_replan_context"] = {
        "command": raw_command,
        "impact_class": str(assessment.get("impact_class", "high")),
        "replan_scope": replan_scope,
        "reasons": list(assessment.get("reasons", [])),
        "turn_index": state.turn_index,
    }
    disruption_event = Event(
        type="major_disruption",
        tags=("story", "major_disruption"),
        message_key="Your choice disrupts the planned arc. The world is already reacting.",
        turn_index=state.turn_index,
        metadata={
            "command": raw_command,
            "assessment": dict(assessment),
        },
    )
    events.append(disruption_event)
    state.append_event(disruption_event)


def _public_event_message(message_key: str) -> str:
    message = message_key.strip()
    if not message:
        return ""
    clarification_messages = {
        "look": "",
        "inventory": "",
        "help": "",
        "unknown_command": (
            "I didn't understand that command. Try LOOK, GO <direction>, TALK <name>, TAKE <item>, or INVENTORY."
        ),
        "move_failed_unknown_destination": "You can't go that way.",
        "move_failed_locked_exit": "That way is locked.",
        "take_failed_missing": "You don't see that here.",
        "take_failed_not_portable": "You can't carry that.",
        "talk_failed_missing": "No one by that name is here.",
        "use_failed_missing_item": "You aren't carrying that item.",
    }
    if message in clarification_messages:
        return clarification_messages[message]
    if message.lower() in _HIDDEN_FREEFORM_MESSAGE_KEYS:
        return ""
    # Hide engine-like keys in normal mode (for example: move_success, take_failed).
    if "_" in message and " " not in message:
        return ""
    return message


def _event_lines(events, debug: bool = False) -> str:
    if not events:
        return ""
    if debug:
        return "\n".join(f"- {event.type}: {event.message_key}" for event in events)
    public_lines = [_public_event_message(event.message_key) for event in events]
    return "\n".join(message for message in public_lines if message)


def _proposal_mode_for_action(action: Action) -> str:
    if action.kind in {ActionKind.MOVE, ActionKind.TAKE, ActionKind.USE}:
        return "physical"
    if action.kind in {ActionKind.LOOK}:
        return "investigation"
    return "scene"


def _preview_state_delta(preview_events: list[Event], skip_facts: tuple[tuple[str, ...], ...] = ()) -> dict[str, Any]:
    skip = set(skip_facts)
    assert_ops: list[dict[str, Any]] = []
    retract_ops: list[dict[str, Any]] = []
    numeric_delta: list[NumericDelta] = []
    reasons: list[str] = []
    for event in preview_events:
        fact_ops = event.metadata.get("fact_ops", ())
        if isinstance(fact_ops, (list, tuple)):
            for fact_op in fact_ops:
                predicate = str(fact_op.get("op", "")).strip()
                fact = tuple(str(part) for part in fact_op.get("fact", ()))
                if not fact or fact in skip:
                    continue
                if predicate == "assert":
                    assert_ops.append({"fact": list(fact)})
                elif predicate == "retract":
                    retract_ops.append({"fact": list(fact)})
        if event.delta_progress != 0.0:
            numeric_delta.append({"key": "progress", "delta": event.delta_progress})
        if event.delta_tension != 0.0:
            numeric_delta.append({"key": "tension", "delta": event.delta_tension})
        if event.type:
            reasons.append(event.type)
    return {
        "assert": assert_ops,
        "retract": retract_ops,
        "numeric_delta": numeric_delta,
        "reasons": reasons,
    }


def _semantic_actions_for_action(
    state: GameState, action: Action, preview_events: list[Event]
) -> tuple[dict[str, Any], ...]:
    room_id = state.player.location
    if action.kind == ActionKind.MOVE and preview_events and preview_events[0].type == "move":
        destination = preview_events[0].entities[1] if len(preview_events[0].entities) > 1 else ""
        return (
            {
                "action_id": f"move-{state.turn_index + 1}",
                "action_type": "move_to",
                "actor_id": "player",
                "target_id": "",
                "item_id": "",
                "location_id": destination,
            },
        )
    if action.kind == ActionKind.TAKE and preview_events and preview_events[0].type == "take":
        item_id = preview_events[0].entities[0] if preview_events[0].entities else action.target
        if item_id in state.world.rooms[room_id].item_ids:
            return (
                {
                    "action_id": f"take-{state.turn_index + 1}",
                    "action_type": "take_item",
                    "actor_id": "player",
                    "target_id": "",
                    "item_id": item_id,
                    "location_id": room_id,
                },
            )
    if action.kind == ActionKind.USE and preview_events and preview_events[0].type == "use":
        item_id = action.target.split(":", maxsplit=1)[0]
        target_id = action.target.split(":", maxsplit=1)[1] if ":" in action.target else ""
        return (
            {
                "action_id": f"use-{state.turn_index + 1}",
                "action_type": "use_item",
                "actor_id": "player",
                "target_id": target_id,
                "item_id": item_id,
                "location_id": room_id,
            },
        )
    return ()


def _structured_turn_proposal_for_action(
    state: GameState, action: Action, preview_events: list[Event]
) -> dict[str, Any]:
    semantic_actions = _semantic_actions_for_action(state, action, preview_events)
    skipped_fact_ops: tuple[tuple[str, ...], ...] = ()
    if semantic_actions:
        semantic_action = semantic_actions[0]
        if semantic_action["action_type"] == "move_to":
            skipped_fact_ops = (("at", "player", semantic_action["location_id"]),)
        elif semantic_action["action_type"] == "take_item":
            skipped_fact_ops = (
                ("room_item", state.player.location, semantic_action["item_id"]),
                ("holding", "player", semantic_action["item_id"]),
            )
    return {
        "turn_id": f"cli-{state.turn_index + 1}",
        "mode": _proposal_mode_for_action(action),
        "player_intent": {
            "summary": action.kind.value,
            "addressed_npc_id": "",
            "target_ids": (),
            "item_ids": (),
            "location_id": state.player.location,
        },
        "scene_framing": {
            "focus": action.raw,
            "dramatic_question": "",
            "player_approach": "",
        },
        "semantic_actions": semantic_actions,
        "state_delta": _preview_state_delta(preview_events, skipped_fact_ops),
        "npc_dialogue": {"speaker_id": "", "text": ""},
        "narration": "",
        "beat_hints": {"escalation": "none", "reveal_thread_ids": (), "obstacle_mode": ""},
    }


def _raw_input_requests_goal(raw_input: str) -> bool:
    lowered = raw_input.lower()
    return re.search(r"\b(goal|goals|objective|objectives)\b", lowered) is not None


def _should_prefer_proposal_resolution(
    raw_input: str,
    fallback_action: Action,
    planner_dialog_payload: dict[str, Any] | None,
    planner_action_payload: dict[str, Any] | None,
) -> bool:
    if planner_action_payload is None or planner_dialog_payload is None:
        return False
    if fallback_action.kind in {ActionKind.HELP, ActionKind.QUIT, ActionKind.SAVE, ActionKind.LOAD}:
        return False

    lowered = raw_input.strip().lower()
    intent = str(planner_action_payload.get("intent", "")).strip().lower()
    speaker = str(planner_dialog_payload.get("speaker", "")).strip().lower()

    conversational_intents = {"ask_about", "greet", "apologize", "threaten", "inspect", "knock"}
    if intent in conversational_intents:
        return True
    if fallback_action.kind == ActionKind.TALK:
        return True
    if speaker not in {"", "narrator", "player"}:
        return True
    return bool(re.search(r"\b(ask|tell|say|speak|talk|who|what|why|how)\b", lowered) or "," in lowered)


def _context_goal_for_turn(raw_input: str, goal: str, turn_index: int) -> str:
    if turn_index <= 0:
        return goal
    if _raw_input_requests_goal(raw_input):
        return goal
    return ""


def _freeform_unavailable_lines(detail: str = "") -> list[str]:
    line = "Story response unavailable: LLM planning is required for this turn."
    if detail:
        return [f"{line} {detail}"]
    return [line]


_PARROTING_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "for",
    "of",
    "in",
    "on",
    "at",
    "is",
    "are",
    "was",
    "were",
    "do",
    "does",
    "did",
    "can",
    "could",
    "would",
    "should",
    "about",
    "which",
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "tell",
    "say",
    "speak",
    "talk",
    "summarize",
    "explain",
    "me",
    "you",
    "your",
}
_CODE_ARTIFACT_TOKEN_PATTERN = re.compile(r"\b[a-z]+(?:[A-Z][a-z0-9]+){1,}\b")
_GARMENT_TOKEN_PATTERN = re.compile(
    r"\b(blouse|skirt|dress|gown|robe|uniform|coat|jacket|shirt|pants|trousers|jeans|boots|hat)\b"
)


def _normalized_dialogue_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _is_conversational_freeform_request(raw_input: str, fallback_action: Action) -> bool:
    lowered = raw_input.strip().lower()
    if fallback_action.kind == ActionKind.TALK:
        return True
    return bool(
        re.search(
            r"\b(ask|tell|say|speak|talk|hello|hi|who|what|when|where|why|how|which|summarize|explain)\b", lowered
        )
        or "," in lowered
    )


def _is_parroting_dialogue(raw_input: str, dialog_payload: dict[str, Any]) -> bool:
    speaker = str(dialog_payload.get("speaker", "")).strip().lower()
    if speaker in {"", "narrator", "player"}:
        return False
    text = str(dialog_payload.get("text", "")).strip()
    if not text:
        return True
    normalized_text = _normalized_dialogue_text(text)
    normalized_input = _normalized_dialogue_text(raw_input)
    if not normalized_text or not normalized_input:
        return False
    if "you asked me" in normalized_text or "you told me" in normalized_text:
        return True
    if normalized_text == normalized_input or normalized_text.startswith(normalized_input):
        return True
    input_tokens = tuple(
        token for token in normalized_input.split() if len(token) >= 3 and token not in _PARROTING_STOPWORDS
    )
    if len(input_tokens) < 3:
        return False
    overlap = sum(1 for token in input_tokens if token in normalized_text)
    text_token_count = len(normalized_text.split())
    return overlap / len(input_tokens) >= 0.85 and text_token_count <= len(input_tokens) + 4


def _targeted_conversation_requires_npc_reply(
    fallback_action: Action,
    planner_action_payload: dict[str, Any],
) -> bool:
    if fallback_action.kind == ActionKind.TALK:
        return True
    intent = str(planner_action_payload.get("intent", "")).strip().lower()
    if intent not in {"ask_about", "greet", "apologize", "threaten", "query"}:
        return False
    targets = planner_action_payload.get("targets", ())
    return isinstance(targets, (list, tuple)) and any(str(target).strip() for target in targets)


def _is_invalid_targeted_dialogue_speaker(
    state: GameState,
    planner_dialog_payload: dict[str, Any],
    planner_action_payload: dict[str, Any],
) -> bool:
    targets = planner_action_payload.get("targets", ())
    if not isinstance(targets, (list, tuple)) or not any(str(target).strip() for target in targets):
        return False
    speaker = _normalized_dialog_speaker_id(
        state,
        str(planner_dialog_payload.get("speaker", "")),
        planner_action_payload,
    )
    if speaker in {"narrator", "player"}:
        return True
    primary_target = _normalized_dialog_speaker_id(
        state,
        str(next((target for target in targets if str(target).strip()), "")),
        planner_action_payload,
    )
    return bool(primary_target and speaker != primary_target)


def _dialogue_contains_code_artifact(dialog_payload: dict[str, Any]) -> bool:
    text = str(dialog_payload.get("text", "")).strip()
    if not text:
        return False
    return _CODE_ARTIFACT_TOKEN_PATTERN.search(text) is not None


def _dialogue_fact_conflict(state: GameState, speaker: str, text: str, topic: str) -> str:
    if topic.strip().lower() != "appearance":
        return ""
    normalized_speaker = normalize_tag(speaker)
    if normalized_speaker not in state.world.npcs:
        return ""
    canonical_appearance = str(state.world.npcs[normalized_speaker].appearance).strip().lower()
    if not canonical_appearance:
        return ""
    canonical_garments = set(_GARMENT_TOKEN_PATTERN.findall(canonical_appearance))
    mentioned_garments = set(_GARMENT_TOKEN_PATTERN.findall(text.lower()))
    if canonical_garments and mentioned_garments and not mentioned_garments.issubset(canonical_garments):
        return "NPC dialogue conflicts with fact-backed appearance details."
    return ""


def _freeform_dialogue_policy_error(
    state: GameState,
    raw_input: str,
    fallback_action: Action,
    planner_dialog_payload: dict[str, Any] | None,
    planner_action_payload: dict[str, Any] | None,
) -> str:
    if planner_dialog_payload is None or planner_action_payload is None:
        return ""
    if not _is_conversational_freeform_request(raw_input, fallback_action):
        return ""
    if _targeted_conversation_requires_npc_reply(
        fallback_action, planner_action_payload
    ) and _is_invalid_targeted_dialogue_speaker(
        state,
        planner_dialog_payload,
        planner_action_payload,
    ):
        return "LLM-authored conversational turns must return an in-character NPC reply, not player or narrator text."
    arguments = planner_action_payload.get("arguments", {})
    planner_source = str(arguments.get("planner_source", "")).strip().lower() if isinstance(arguments, dict) else ""
    targets = planner_action_payload.get("targets", ())
    has_target = isinstance(targets, (list, tuple)) and any(str(target).strip() for target in targets)
    if planner_source == "fallback" and has_target:
        return "LLM-authored NPC dialogue is required for conversational turns."
    if _is_parroting_dialogue(raw_input, planner_dialog_payload):
        return "Conversational NPC dialogue must answer in character instead of repeating the player's prompt."
    if _dialogue_contains_code_artifact(planner_dialog_payload):
        return "Conversational NPC dialogue must stay in-world and must not leak code or implementation artifacts."
    speaker = str(planner_dialog_payload.get("speaker", "")).strip()
    topic = str(arguments.get("topic", "")).strip() if isinstance(arguments, dict) else ""
    fact_conflict = _dialogue_fact_conflict(state, speaker, str(planner_dialog_payload.get("text", "")), topic)
    if fact_conflict:
        return fact_conflict
    return ""


def _has_bounded_dialogue_event(events: list[Event], debug: bool = False) -> bool:
    if debug:
        return False
    for event in events:
        message = _public_event_message(event.message_key)
        if ' says: "' in message:
            action_proposal = event.metadata.get("action_proposal", {})
            arguments = action_proposal.get("arguments", {}) if isinstance(action_proposal, dict) else {}
            planner_source = str(arguments.get("planner_source", "")).strip().lower()
            if planner_source == "fallback":
                continue
            return True
    return False


def _suppress_repeated_goal_copy(lines: list[str], raw_input: str, active_goal: str) -> list[str]:
    if _raw_input_requests_goal(raw_input):
        return lines

    lowered_goal = active_goal.lower().strip()
    filtered: list[str] = []
    for line in lines:
        lowered = line.lower()
        if "first practical objective" in lowered or "immediate objective" in lowered:
            continue
        if lowered_goal and lowered_goal in lowered and ("goal" in lowered or "objective" in lowered):
            continue
        filtered.append(line)
    return filtered


def _contains_repeated_goal_copy(text: str, raw_input: str, active_goal: str) -> bool:
    if _raw_input_requests_goal(raw_input):
        return False
    lowered = text.lower()
    if "first practical objective" in lowered or "immediate objective" in lowered:
        return True
    lowered_goal = active_goal.lower().strip()
    return bool(lowered_goal and lowered_goal in lowered and ("goal" in lowered or "objective" in lowered))


def _write_transcript_line(handle: TextIO | None, line: str) -> None:
    if handle is None:
        return
    handle.write(line + "\n")


def _emit_cli_line(console: Console, line: str) -> None:
    for paragraph in line.split("\n"):
        console.print(paragraph, highlight=False, markup=False, overflow="fold")


def _sanitize_narration_for_player(narration: str, debug: bool, raw_input: str = "") -> str:
    if debug:
        return narration
    if re.search(r"\bbeat at\b", narration.lower()):
        return ""
    if player_facing_presentation_issues([narration]):
        return ""
    if is_player_statement_echo(raw_input, narration):
        return ""
    return narration


def _narration_references_action(narration: str, action_raw: str) -> bool:
    narration_tokens = {token for token in re.findall(r"[a-z0-9]+", narration.lower()) if len(token) >= 4}
    action_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", action_raw.lower())
        if len(token) >= 4 and token not in {"look", "talk", "speak", "move", "north", "south", "east", "west"}
    }
    if not action_tokens:
        return True
    return bool(narration_tokens.intersection(action_tokens))


def _ensure_action_grounded_narration(narration: str, action: Action) -> str:
    if not narration:
        return narration
    if action.kind in {ActionKind.LOOK, ActionKind.HELP, ActionKind.INVENTORY, ActionKind.SAVE, ActionKind.LOAD}:
        return narration
    if _narration_references_action(narration, action.raw):
        return narration
    return f'You act on "{action.raw}". {narration}'


def _should_discard_failed_narration(
    judge_decision: JudgeDecision,
    coherence_telemetry: CoherenceTelemetry,
) -> bool:
    return (
        str(judge_decision["status"]) == "failed"
        and str(coherence_telemetry["hard_fail_reason"]) == "BUDGET_WALL_CLOCK_TIMEOUT"
    )


def _transcript_command_echo(raw_command: str) -> str:
    return f">{raw_command.strip().upper()}"


def _write_transcript_command_echo(handle: TextIO | None, raw_command: str) -> None:
    _write_transcript_line(handle, "")
    _write_transcript_line(handle, _transcript_command_echo(raw_command))


def _target_from_proposal(action_proposal: dict[str, Any]) -> str:
    targets = tuple(str(target).strip().lower() for target in action_proposal.get("targets", ()) if str(target).strip())
    if not targets:
        return ""
    return targets[0]


def _action_from_proposal(raw: str, action_proposal: dict[str, Any]) -> Action:
    intent = str(action_proposal.get("intent", "")).strip().lower()
    target = _target_from_proposal(action_proposal)

    if intent in {"look"}:
        return Action(ActionKind.LOOK, raw=raw)
    if intent in {"inventory", "inv"}:
        return Action(ActionKind.INVENTORY, raw=raw)
    if intent in {"help", "hint"}:
        return Action(ActionKind.HELP, raw=raw)
    if intent in {"go", "move", "travel", "walk"} and target:
        return Action(ActionKind.MOVE, target=target, raw=raw)
    if intent in {"take", "get", "grab", "pick_up", "pickup", "acquire"} and target:
        return Action(ActionKind.TAKE, target=target, raw=raw)
    if intent in {"talk", "speak"} and target:
        return Action(ActionKind.TALK, target=target, raw=raw)
    if intent in {"use"} and target:
        secondary = str(action_proposal.get("arguments", {}).get("target", "")).strip().lower()
        combined = f"{target}:{secondary}" if secondary else target
        return Action(ActionKind.USE, target=combined, raw=raw)
    return Action(ActionKind.UNKNOWN, raw=raw)


def _build_narrator(mode: str = "cloudflare") -> Narrator:
    if mode != "cloudflare":
        raise ValueError(f"Narrator mode '{mode}' is not supported.")
    return CloudflareWorkersAIAdapter()


def _build_memory_tag_set(state: GameState, action) -> tuple[str, ...]:
    room = state.world.rooms[state.player.location]
    action_target = normalize_tag(action.target) if action.target else ""
    goal_words = tuple(normalize_tag(word) for word in state.active_goal.split() if word)[:2]
    ordered_tags: list[str] = [
        f"beat_{state.beat_history[-1]}" if state.beat_history else "beat_unknown",
        f"goal_{goal_words[0]}" if goal_words else "goal",
    ]
    if action_target:
        ordered_tags.append(action_target)
        ordered_tags.append(f"npc_{action_target}")
    for npc in room.npc_ids:
        ordered_tags.append(npc)
        ordered_tags.append(f"npc_{npc}")
    ordered_tags.append(f"room_{state.player.location}")

    deduped: list[str] = []
    for tag in ordered_tags:
        if tag and tag not in deduped:
            deduped.append(tag)
    return tuple(deduped[:MAX_MEMORY_NOTES])


class SaveStore(Protocol):
    def save_run(
        self,
        slot: str,
        state: GameState,
        rng: Random,
        raw_command: str = "save",
        action_kind: str = "save",
        beat_type: str | None = None,
        template_key: str | None = None,
        transcript: list[str] | None = None,
        judge_decision: dict[str, str] | None = None,
    ) -> None: ...

    def load_run(self, slot: str) -> tuple[GameState, Random]: ...


def _judge_decision_for_persistence(state: GameState) -> dict[str, str] | None:
    if state.last_judge_decision is None:
        return None
    if state.last_judge_decision.get("status") != "accepted":
        return None
    return state.last_judge_decision


def run_turn(
    state: GameState,
    raw: str,
    rng: Random,
    narrator: Narrator,
    debug: bool = False,
    save_store: SaveStore | None = None,
    memory_store: MemoryStore | None = None,
    memory_slot: str = "default",
    freeform_adapter: FreeformProposalAdapter = DEFAULT_FREEFORM_ADAPTER,
    output_editor: OutputEditor | None = None,
    story_director: StoryDirector | None = None,
    _confirmed_high_impact: bool = False,
    _confirmed_assessment: ImpactAssessment | None = None,
):
    record("complete_turn", command=raw.strip().lower()[:80])
    raw_input = raw.strip()
    lowered_input = raw_input.lower()
    active_freeform_adapter = freeform_adapter
    if state.pending_high_impact_command:
        if lowered_input in _PROCEED_WORDS:
            confirmed_command = state.pending_high_impact_command
            confirmed_assessment = _impact_assessment_from_mapping(state.pending_high_impact_assessment)
            resumed_state = state.clone()
            _clear_pending_high_impact(resumed_state)
            return run_turn(
                resumed_state,
                confirmed_command,
                rng,
                narrator,
                debug=debug,
                save_store=save_store,
                memory_store=memory_store,
                memory_slot=memory_slot,
                freeform_adapter=active_freeform_adapter,
                output_editor=output_editor,
                story_director=story_director,
                _confirmed_high_impact=True,
                _confirmed_assessment=confirmed_assessment,
            )
        if lowered_input in _CANCEL_WORDS:
            canceled_state = state.clone()
            _clear_pending_high_impact(canceled_state)
            return canceled_state, ["Action canceled. Story plan remains unchanged."], raw_input, "impact_gate", True
        return (
            state,
            ["A high-impact action is pending confirmation. Type PROCEED to continue or CANCEL to abort."],
            raw_input,
            "impact_gate",
            True,
        )

    control_action = parse_control_command(raw)
    if control_action.kind == ActionKind.HELP:
        return (
            state,
            [
                "Controls: /help, /save <slot>, /load <slot>, /quit. Write anything else as an in-world action or dialogue."
            ],
            control_action.raw,
            "help",
            True,
        )
    if control_action.kind == ActionKind.QUIT:
        return state, ["Goodbye."], "", "", False

    if control_action.kind == ActionKind.SAVE:
        if not control_action.target:
            return state, ["Usage: save <slot>."], control_action.raw, "save", True
        if save_store is None:
            return state, ["Save requires --save-db <path>."], control_action.raw, "save", True
        try:
            save_store.save_run(
                control_action.target,
                state,
                rng,
                raw_command=control_action.raw,
                action_kind="save",
                judge_decision=_judge_decision_for_persistence(state),
            )
            return state, [f"Saved to slot '{control_action.target}'."], control_action.raw, "save", True
        except Exception as exc:
            return state, [f"Failed to save: {exc}"], control_action.raw, "save", True

    if control_action.kind == ActionKind.LOAD:
        if not control_action.target:
            return state, ["Usage: load <slot>."], control_action.raw, "load", True
        if save_store is None:
            return state, ["Load requires --save-db <path>."], control_action.raw, "load", True
        try:
            state, loaded_rng = save_store.load_run(control_action.target)
            rng.setstate(loaded_rng.getstate())
            return (
                state,
                [f"Loaded from slot '{control_action.target}'."],
                control_action.raw,
                "load",
                True,
            )
        except ValueError as exc:
            return state, [f"Could not load slot '{control_action.target}': {exc}"], control_action.raw, "load", True
        except Exception as exc:
            return state, [f"Failed to load: {exc}"], control_action.raw, "load", True

    editor = build_output_editor() if output_editor is None else output_editor
    director = StoryDirector("cloudflare", editor) if story_director is None else story_director
    preturn_state = state
    replan_event = None
    if state.player.flags.get("story_replan_required", False):
        preturn_state = state.clone()
        replan_event = director.replan_if_needed(preturn_state)
    if replan_event is not None:
        preturn_state.append_event(replan_event)
    direct_addressed_npc_id = addressed_visible_npc_id(preturn_state, raw_input)

    planner_dialog_payload: dict[str, Any] | None = None
    planner_action_payload: dict[str, Any] | None = None
    accepted_proposal_text = ""
    planner_parse_error = ""
    staging_trace: dict[str, Any] = {}
    fallback_action = Action(ActionKind.UNKNOWN, raw=raw_input)
    effective_action = fallback_action
    freeform_policy_debug: dict[str, Any] | None = None
    semantic_destination = _semantic_exit_direction(preturn_state, raw_input)
    named_destination = semantic_destination and any(
        label in raw_input.lower()
        for label in (
            semantic_destination.replace("_", " "),
            preturn_state.world.rooms[semantic_destination].name.lower(),
        )
    )
    try:
        if named_destination or _takeable_item_for_input(preturn_state, raw_input):
            planner_dialog_payload, planner_action_payload = RuleBasedFreeformProposalAdapter().propose(
                preturn_state, raw_input
            )
            planner_action_payload = _normalized_movement_action_payload(
                preturn_state, raw_input, planner_action_payload
            )
        elif type(active_freeform_adapter) is LlmFreeformProposalAdapter:
            planner_dialog_payload, planner_action_payload = active_freeform_adapter.propose(
                preturn_state,
                raw_input,
                lambda dialog, action: resolve_freeform_roleplay_with_proposals(
                    preturn_state, raw_input, dialog, action
                ),
            )
            staging_trace = dict(active_freeform_adapter.last_staging_trace)
        else:
            planner_dialog_payload, planner_action_payload = active_freeform_adapter.propose(preturn_state, raw_input)
        normalized_action_payload = parse_action_proposal(
            bind_direct_npc_conversation_target(
                preturn_state,
                raw_input,
                _normalized_movement_action_payload(preturn_state, raw_input, planner_action_payload),
            )
        )
        planner_action_payload = normalized_action_payload
        dialogue_policy_error = _freeform_dialogue_policy_error(
            preturn_state,
            raw_input,
            fallback_action,
            planner_dialog_payload,
            normalized_action_payload,
        )
        if dialogue_policy_error:
            planner_dialog_payload = None
            planner_action_payload = None
            planner_parse_error = f"ORDINARY_TURN_POLICY_REJECTED: {dialogue_policy_error}"
            raise RuntimeError(planner_parse_error)
        effective_action = _action_from_proposal(raw_input, normalized_action_payload)
    except Exception as exc:
        planner_parse_error = str(exc)

    impact_assessment: ImpactAssessment = (
        _confirmed_assessment
        if _confirmed_assessment is not None
        else assess_player_command(state, effective_action.raw, effective_action)
    )
    if not _confirmed_high_impact and requires_high_impact_confirmation(impact_assessment):
        blocked_state = state.clone()
        blocked_state.pending_high_impact_command = effective_action.raw
        blocked_state.pending_high_impact_assessment = dict(impact_assessment)
        return blocked_state, _high_impact_warning_lines(impact_assessment), effective_action.raw, "impact_gate", True

    if planner_dialog_payload is None or planner_action_payload is None:
        detail = planner_parse_error.strip()
        return state.clone(), _freeform_unavailable_lines(detail), raw_input, "freeform_roleplay", True
    freeform = resolve_freeform_roleplay_with_proposals(
        preturn_state,
        raw_input,
        planner_dialog_payload,
        planner_action_payload,
        staging_trace,
    )
    next_state = freeform["state"]
    events = list(freeform["events"])
    accepted_proposal_text = str(freeform["accepted_prose"]).strip()
    if is_player_statement_echo(raw_input, accepted_proposal_text):
        return (
            state.clone(),
            _freeform_unavailable_lines("ORDINARY_TURN_POLICY_REJECTED: player-statement echo"),
            raw_input,
            "freeform_roleplay",
            True,
        )
    freeform_policy_debug = {
        "action_proposal": dict(freeform["action_proposal"]),
        "state_update_envelope": dict(freeform["state_update_envelope"]),
        "fact_ops": list(freeform["event"].metadata.get("fact_ops", [])),
        "planner_error": planner_parse_error,
        "staging_trace": staging_trace,
        "proposal_first": True,
        "story_delta": {
            "progress": freeform["event"].delta_progress,
            "tension": freeform["event"].delta_tension,
        },
    }
    if replan_event is not None:
        events.insert(0, replan_event)
    beat_type = "freeform_roleplay"
    template_key = "freeform_roleplay"
    effective_action = _action_from_proposal(raw_input, freeform["action_proposal"])

    memory_fragments: tuple[str, ...] = ()
    if memory_store is not None:
        memory_fragments = memory_store.retrieve(memory_slot, _build_memory_tag_set(next_state, effective_action))

    context = build_narration_context(next_state, effective_action, beat_type, memory_fragments)
    context = replace(
        context,
        goal=_context_goal_for_turn(raw_input, context.goal, next_state.turn_index),
    )
    judge_decision: JudgeDecision = {
        "status": "failed",
        "total_score": 0,
        "threshold": 80,
        "round_index": 1,
        "critic_ids": (),
        "critical_floors": {"continuity": 70, "causality": 70},
        "critic_reports": (),
        "judge": "coherence_gate",
        "rationale": "Narration generation failed before acceptance.",
        "rubric_components": {"continuity": 0, "causality": 0, "dialogue_fit": 0},
        "decision_id": "judge-error",
    }
    coherence_telemetry: CoherenceTelemetry = {
        "critique_rounds": 0,
        "token_spend": {"narrator": 0, "critics": 0},
        "elapsed_ms": 0,
        "hard_fail_reason": "NARRATOR_RUNTIME_ERROR",
    }
    narration = freeform["event"].message_key if direct_addressed_npc_id else accepted_proposal_text
    judge_decision["status"] = "accepted"
    judge_decision["decision_id"] = "post-commit-proposal"
    coherence_telemetry["hard_fail_reason"] = ""

    if _confirmed_high_impact:
        _record_major_disruption(next_state, events, effective_action.raw, impact_assessment)

    narration = _sanitize_narration_for_player(narration, debug=debug, raw_input=raw_input)
    if not direct_addressed_npc_id:
        narration = _ensure_action_grounded_narration(narration, effective_action)

    # Room identity, exits, inventory, visible entities, and event state remain
    # in the observer-scoped narration context. They are continuity inputs, not
    # a second player-facing prose channel. Ordinary turns therefore expose
    # only generated narration (or an addressed NPC's generated reply).
    lines: list[str] = [narration.strip()] if narration.strip() else []

    if debug:
        lines.extend(story_status_lines(next_state))

    if debug:
        lines.append(
            f"[debug] turn={next_state.turn_index} phase={get_phase(next_state.progress)} "
            f"tension={next_state.tension:.2f} progress={next_state.progress:.2f} "
            f"beat={beat_type} plot_event={template_key}"
        )
        lines.append(f"[debug] event_types={tuple(event.type for event in events)}")
        context_keys = tuple(context.as_dict().keys()) if context is not None else ("freeform_roleplay",)
        lines.append(f"[debug] context_keys={context_keys}")
        if freeform_policy_debug is not None:
            proposal = freeform_policy_debug["action_proposal"]
            envelope = freeform_policy_debug["state_update_envelope"]
            lines.append(
                "[debug] freeform_policy "
                f"intent={proposal.get('intent', '')} "
                f"targets={tuple(proposal.get('targets', ()))} "
                f"reasons={tuple(envelope.get('reasons', ()))} "
                f"fact_ops={tuple(freeform_policy_debug['fact_ops'])} "
                f"story_delta={freeform_policy_debug['story_delta']}"
            )
        lines.append(
            f"[debug] judge_status={judge_decision['status']} total={judge_decision['total_score']} "
            f"threshold={judge_decision['threshold']} round={judge_decision['round_index']} "
            f"critics={judge_decision['critic_ids']} components={judge_decision['rubric_components']} "
            f"decision_id={judge_decision['decision_id']}"
        )
        lines.append(
            f"[debug] coherence_budget rounds={coherence_telemetry['critique_rounds']} "
            f"tokens={coherence_telemetry['token_spend']} elapsed_ms={coherence_telemetry['elapsed_ms']} "
            f"hard_fail_reason={coherence_telemetry['hard_fail_reason']}"
        )
        debug_trace = {
            "turn": next_state.turn_index,
            "phase": str(get_phase(next_state.progress)),
            "tension": round(next_state.tension, 4),
            "progress": round(next_state.progress, 4),
            "beat": beat_type,
            "plot_event": template_key,
            "events": [event.type for event in events],
            "freeform_policy": freeform_policy_debug,
            "judge": {
                "status": judge_decision["status"],
                "total_score": judge_decision["total_score"],
                "threshold": judge_decision["threshold"],
                "round_index": judge_decision["round_index"],
                "critic_ids": list(judge_decision["critic_ids"]),
                "rubric_components": judge_decision["rubric_components"],
                "decision_id": judge_decision["decision_id"],
            },
            "coherence": coherence_telemetry,
        }
        lines.append("[debug-json] " + json.dumps(debug_trace, sort_keys=True))

    if memory_store is not None:
        memory_store.ingest_events(memory_slot, next_state, events)

    next_state.last_judge_decision = {
        "decision_id": str(judge_decision["decision_id"]),
        "status": str(judge_decision["status"]),
        "judge": "director",
        "rationale": str(judge_decision.get("rationale", "")),
    }

    lines = [line for line in lines if line]
    lines = _suppress_repeated_goal_copy(lines, raw_input, next_state.active_goal)
    if not lines:
        lines = []

    reviewed_lines = [line for line in lines if line]
    reviewed_lines = _suppress_repeated_goal_copy(reviewed_lines, raw_input, next_state.active_goal)
    if output_editor is not None:
        # Explicitly injected editors are retained as a compatibility adapter;
        # production surfaces do not inject one on the ordinary path.
        reviewed_lines = output_editor.review_turn(
            reviewed_lines,
            next_state.active_goal,
            next_state.turn_index,
            debug,
        )
    return next_state, reviewed_lines, effective_action.raw, beat_type, True


def run_replay(
    seed: int,
    commands: list[str],
    genre: str = "mystery",
    session_length: int | str = "medium",
    tone: str = "neutral",
    debug: bool = False,
    save_db: Path | None = None,
    memory_db: Path | None = None,
    memory_slot: str = "default",
    narrator: Narrator | None = None,
) -> GameState:
    rng = Random(seed)
    state = build_default_state(seed, genre=genre, session_length=session_length, tone=tone)
    active_narrator: Narrator = _build_narrator() if narrator is None else narrator
    save_store: SqliteSaveStore | None = SqliteSaveStore(save_db) if save_db is not None else None
    memory_store: SqliteVectorMemory | None = SqliteVectorMemory(memory_db) if memory_db is not None else None
    try:
        for command in commands:
            state, _output, _action, _beat, _continued = run_turn(
                state,
                command,
                rng,
                active_narrator,
                debug=debug,
                save_store=save_store,
                memory_store=memory_store,
                memory_slot=memory_slot,
            )
            if not _continued:
                break
    finally:
        if save_store is not None:
            save_store.close()
        if memory_store is not None:
            memory_store.close()
    return state


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Freytag text adventure")
    parser.add_argument("--seed", type=int, default=123, help="Random seed for deterministic play")
    parser.add_argument(
        "--genre",
        choices=(
            "sci-fi",
            "mystery",
            "romance",
            "adventure",
            "action",
            "suspense",
            "drama",
            "fantasy",
            "horror",
            "thriller",
        ),
        default="mystery",
        help="Story genre used for startup curve selection.",
    )
    parser.add_argument(
        "--session-length",
        choices=("short", "medium", "long"),
        default="medium",
        help="Session-length bucket used for startup curve selection.",
    )
    parser.add_argument(
        "--tone",
        choices=("neutral", "dark", "light", "romantic", "tense", "mysterious", "epic"),
        default="neutral",
        help="Optional tone preference used for outline selection.",
    )
    parser.add_argument("--replay", type=Path, default=None, help="Replay commands from a file")
    parser.add_argument("--save-db", type=Path, default=None, help="SQLite save file path")
    parser.add_argument("--memory-db", type=Path, default=None, help="SQLite vector memory file path")
    parser.add_argument("--memory-slot", default="default", help="Memory slot key for retrieval and storage")
    parser.add_argument("--debug", action="store_true", help="Print phase and beat diagnostics")
    parser.add_argument(
        "--autosave-slot",
        default=None,
        help="Auto-save state each turn to this slot (optional).",
    )
    parser.add_argument("--transcript", type=Path, default=None, help="Write transcript to a file")

    args = parser.parse_args(argv)
    console = Console()

    state = build_default_state(
        args.seed,
        genre=args.genre,
        session_length=args.session_length,
        tone=args.tone,
    )
    rng = Random(args.seed)
    narrator: Narrator = _build_narrator("cloudflare")
    freeform_adapter = LlmFreeformProposalAdapter("cloudflare")
    output_editor = build_output_editor()
    story_director = StoryDirector("cloudflare", output_editor)
    save_store: SqliteSaveStore | None = SqliteSaveStore(args.save_db) if args.save_db is not None else None
    memory_store: SqliteVectorMemory | None = SqliteVectorMemory(args.memory_db) if args.memory_db is not None else None
    autosave_slot = args.autosave_slot
    memory_slot = args.memory_slot

    transcript_path = args.transcript
    if transcript_path is None and args.replay is not None:
        transcript_path = Path("runs") / f"replay_seed_{args.seed}.txt"

    transcript_handle: TextIO | None = None
    if transcript_path is not None:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_handle = transcript_path.open("w", encoding="utf-8")

    try:
        setup_lines = story_director.compose_opening(state)
        for line in _with_paragraph_spacing(setup_lines):
            _emit_cli_line(console, line)
            _write_transcript_line(transcript_handle, line)

        if args.replay is not None:
            commands = [line.strip() for line in args.replay.read_text().splitlines() if line.strip()]
            for command in commands:
                _write_transcript_command_echo(transcript_handle, command)
                state, lines, _action, _beat, _ = run_turn(
                    state,
                    command,
                    rng,
                    narrator,
                    freeform_adapter=freeform_adapter,
                    debug=args.debug,
                    save_store=save_store,
                    memory_store=memory_store,
                    memory_slot=memory_slot,
                    output_editor=output_editor,
                    story_director=story_director,
                )
                if autosave_slot is not None and save_store is not None:
                    save_store.save_run(
                        autosave_slot,
                        state,
                        rng,
                        raw_command=command,
                        action_kind="autosave",
                        judge_decision=_judge_decision_for_persistence(state),
                    )
                for line in lines:
                    _emit_cli_line(console, line)
                    _write_transcript_line(transcript_handle, line)
            return

        while True:
            raw = input("> ")
            _write_transcript_command_echo(transcript_handle, raw)
            state, lines, action_raw, _, continued = run_turn(
                state,
                raw,
                rng,
                narrator,
                freeform_adapter=freeform_adapter,
                debug=args.debug,
                save_store=save_store,
                memory_store=memory_store,
                memory_slot=memory_slot,
                output_editor=output_editor,
                story_director=story_director,
            )
            for line in lines:
                _emit_cli_line(console, line)
                _write_transcript_line(transcript_handle, line)
            if action_raw.lower() in {"quit", "exit", "leave"}:
                break
            if not continued:
                break

            if autosave_slot is not None and save_store is not None:
                save_store.save_run(
                    autosave_slot,
                    state,
                    rng,
                    raw_command=raw,
                    action_kind="autosave",
                    judge_decision=_judge_decision_for_persistence(state),
                )
    finally:
        if transcript_handle is not None:
            transcript_handle.close()
        if save_store is not None:
            save_store.close()
        if memory_store is not None:
            memory_store.close()


if __name__ == "__main__":
    main()
