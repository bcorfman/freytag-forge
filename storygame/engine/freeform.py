from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol, TypedDict

from storygame.engine.facts import apply_fact_ops, player_location, room_items, room_npcs
from storygame.engine.interfaces import parse_action_proposal, parse_dialog_proposal, parse_state_update_envelope
from storygame.engine.parser import ActionKind, parse_command
from storygame.engine.state import Event, GameState
from storygame.llm.story_agents.agents import _chat_complete as _story_agent_chat_complete
from storygame.llm.story_agents.agents import _json_from_text as _story_agent_json_from_text

_TOPIC_TOKEN = re.compile(r"[^a-z0-9]+")
_ASK_TARGET_PATTERN = re.compile(r"\bask\s+([a-z0-9_ .'-]{1,60}?)(?:\s+about\b|$)", re.IGNORECASE)
_DIRECT_ADDRESS_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z .'-]{0,60})\s*,")
_ALLOWED_TOPIC_FLAGS = {
    "signal",
    "rumor",
    "rumors",
    "ledger",
    "appearance",
    "objective",
    "bell",
}
_ALLOWED_INTENTS = {"ask_about", "greet", "apologize", "threaten"}
_PER_TURN_DELTA_BOUND = 0.15
_TOPIC_STOPWORDS = {"the", "a", "an", "about", "of", "to"}
_PROGRESSIVE_TOKENS = {"inspect", "examine", "investigate", "search", "review", "analyze", "question", "ask"}
_ESCALATION_TOKENS = {"threaten", "attack", "assault", "harm", "violence"}
_CASE_FILE_COMMAND = re.compile(r"\b(read|review|examine|inspect)\b.*\bcase\s+file\b")
_LEDGER_PAGE_COMMAND = re.compile(r"\b(read|review|examine|inspect)\b.*\bledger\s+page\b")
_QUOTED_DIALOGUE_PATTERN = re.compile(r"""["']([^"']+)["']""")
_PLACE_QUESTION_PATTERN = re.compile(r"\b(this place|here|what do you make of|what do you think of)\b", re.IGNORECASE)
_APPEARANCE_QUESTION_PATTERN = re.compile(
    r"\b(what are you wearing|what're you wearing|wearing|clothes|clothing|coat|dress|uniform|outfit)\b",
    re.IGNORECASE,
)


def _short_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


class FreeformProposalAdapter(Protocol):
    def propose(self, state: GameState, raw_input: str) -> tuple[dict[str, Any], dict[str, Any]]: ...


class FreeformResolution(TypedDict):
    state: GameState
    event: Event
    action_proposal: dict[str, Any]
    dialog_proposal: dict[str, Any]
    state_update_envelope: dict[str, Any]


class RuleBasedFreeformProposalAdapter:
    def propose(self, state: GameState, raw_input: str) -> tuple[dict[str, Any], dict[str, Any]]:
        text = raw_input.strip().lower()
        words = text.split()
        first = words[0] if words else ""
        command_like_heads = {
            "look",
            "help",
            "inventory",
            "inv",
            "go",
            "move",
            "travel",
            "walk",
            "north",
            "south",
            "east",
            "west",
            "up",
            "down",
            "take",
            "get",
            "grab",
            "pick",
            "acquire",
            "use",
            "l",
            "h",
            "?",
            "i",
            "n",
            "s",
            "e",
            "w",
            "u",
            "d",
        }
        single_token_only = {"l", "h", "?", "i", "n", "s", "e", "w", "u", "d"}
        if first in command_like_heads and (first not in single_token_only or len(words) == 1):
            parsed = parse_command(raw_input)
            if parsed.kind in {
                ActionKind.LOOK,
                ActionKind.HELP,
                ActionKind.INVENTORY,
                ActionKind.MOVE,
                ActionKind.TAKE,
                ActionKind.TALK,
                ActionKind.USE,
            }:
                canonical_targets: list[str] = []
                if parsed.target:
                    if parsed.kind == ActionKind.USE and ":" in parsed.target:
                        canonical_targets = [segment for segment in parsed.target.split(":", maxsplit=1) if segment]
                    else:
                        canonical_targets = [parsed.target]
                action_payload = {
                    "intent": parsed.kind.value,
                    "targets": canonical_targets,
                    "arguments": {},
                    "proposed_effects": [f"{parsed.kind.value}:{canonical_targets[0] if canonical_targets else 'none'}"],
                }
                dialog_payload = {
                    "speaker": "narrator",
                    "text": "You focus on the immediate action.",
                    "tone": "in_world",
                }
                return dialog_payload, action_payload

        visible_npcs = room_npcs(state, player_location(state))
        direct_address_match = _DIRECT_ADDRESS_PATTERN.match(raw_input)
        direct_address_candidate = direct_address_match.group(1).strip() if direct_address_match is not None else ""

        target = _visible_npc_match(state, direct_address_candidate) if direct_address_candidate else ""
        explicit_target_requested = bool(direct_address_candidate)
        conversation_head = first in {"talk", "speak", "speak_to", "speakto"}
        ask_target_match = _ASK_TARGET_PATTERN.search(raw_input)
        if not target and ask_target_match is not None:
            explicit_target_requested = True
            target = _visible_npc_match(state, ask_target_match.group(1))
        if not target:
            for npc_id in visible_npcs:
                npc = state.world.npcs.get(npc_id)
                if npc_id in text:
                    target = npc_id
                    break
                if npc is None:
                    continue
                normalized_name = _normalize_target(npc.name)
                if normalized_name and normalized_name in text:
                    target = npc_id
                    break
                if any(name_part and name_part in text for name_part in (_normalize_target(part) for part in npc.name.split())):
                    target = npc_id
                    break
        if not target and visible_npcs and not explicit_target_requested:
            target = visible_npcs[0]

        intent = "ask_about"
        topic = "rumors"
        if conversation_head:
            intent = "greet"
            topic = ""
            if "about" in text:
                intent = "ask_about"
                topic = text.split("about", 1)[1].strip() or "rumors"
        if re.search(r"\b(examine|inspect|read|review)\b", text):
            intent = "inspect"
            topic = ""
        elif re.search(r"\bknock\b", text):
            intent = "knock"
            topic = ""
        elif text.startswith(("hi", "hello", "greet")):
            intent = "greet"
            topic = ""
        elif "sorry" in text or "apolog" in text:
            intent = "apologize"
            topic = ""
        elif "threat" in text or "warn" in text:
            intent = "threaten"
            topic = ""
        elif _APPEARANCE_QUESTION_PATTERN.search(raw_input):
            topic = "appearance"
        elif re.search(r"\b(goal|goals|objective|objectives)\b", text):
            topic = "objective"
        elif "about" in text:
            topic = text.split("about", 1)[1].strip() or "rumors"
        elif _PLACE_QUESTION_PATTERN.search(raw_input):
            topic = "place"

        targets: list[str] = [target] if target else []
        if intent in {"inspect", "knock"}:
            if "case file" in text:
                targets = ["case_file"]
            elif "ledger page" in text:
                targets = ["ledger_page"]
            elif "door" in text:
                targets = ["door"]
            else:
                targets = []

        action_payload = {
            "intent": intent,
            "targets": targets,
            "arguments": {"topic": topic} if topic else {},
            "proposed_effects": [f"{intent}:{targets[0] if targets else 'none'}"],
        }
        speaker = target or "narrator"
        response = _dialog_line(intent=intent, target=target, topic=topic, state=state)
        if explicit_target_requested and not target:
            response = "No one here answers that. Try speaking to someone in the room."
        dialog_payload = {"speaker": speaker, "text": response, "tone": "in_world"}
        return dialog_payload, action_payload


def _resolve_freeform_mode() -> str:
    configured = os.getenv("FREYTAG_NARRATOR", "").strip().lower()
    if configured in {"openai", "ollama"}:
        return configured
    if os.getenv("OPENAI_API_KEY", "").strip():
        return "openai"
    if os.getenv("OLLAMA_BASE_URL", "").strip() or os.getenv("OLLAMA_MODEL", "").strip():
        return "ollama"
    return "openai"


def _normalize_target(value: str) -> str:
    return _TOPIC_TOKEN.sub("_", value.strip().lower()).strip("_")


def _visible_npc_match(state: GameState, raw_target: str) -> str:
    candidate = _normalize_target(raw_target)
    if not candidate:
        return ""

    visible_npcs = room_npcs(state, player_location(state))
    for npc_id in visible_npcs:
        if npc_id == candidate:
            return npc_id
        npc = state.world.npcs.get(npc_id)
        if npc is None:
            continue
        if _normalize_target(npc.name) == candidate:
            return npc_id
        if candidate in tuple(_normalize_target(part) for part in npc.name.split()):
            return npc_id
    return ""


def _freeform_planner_prompt(state: GameState, raw_input: str) -> tuple[str, str]:
    room = state.world.rooms[state.player.location]
    npc_facts = [
        {
            "id": npc_id,
            "name": state.world.npcs[npc_id].name,
            "identity": state.world.npcs[npc_id].identity,
            "description": state.world.npcs[npc_id].description,
        }
        for npc_id in room.npc_ids
        if npc_id in state.world.npcs
    ]
    payload = {
        "player_input": raw_input,
        "goal": state.active_goal,
        "turn_index": state.turn_index,
        "room": {
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "visible_npc_ids": list(room.npc_ids),
            "visible_item_ids": list(room.item_ids),
            "exits": sorted(room.exits.keys()),
        },
        "npc_facts": npc_facts,
        "inventory": list(state.player.inventory),
    }
    system = (
        "You are Freeform Action Planner Agent. "
        "Return JSON only with keys dialog_proposal and action_proposal. "
        "dialog_proposal requires: speaker, text, tone. "
        "action_proposal requires: intent, targets, arguments, proposed_effects. "
        "Use only entities from provided context. "
        "For uncertain targets, use an empty targets list and a generic intent."
    )
    return system, json.dumps(payload, ensure_ascii=True)


def _normalize_action_payload(action_payload: dict[str, Any]) -> dict[str, Any]:
    intent = _normalize_target(str(action_payload.get("intent", "")))
    targets = [_normalize_target(str(target)) for target in action_payload.get("targets", [])]
    arguments = {str(k): str(v) for k, v in action_payload.get("arguments", {}).items()}
    proposed_effects = [str(effect) for effect in action_payload.get("proposed_effects", [])]
    if intent:
        arguments.setdefault("planner_intent_raw", intent)
    return {
        "intent": intent or "freeform",
        "targets": [target for target in targets if target],
        "arguments": arguments,
        "proposed_effects": proposed_effects,
    }


class LlmFreeformProposalAdapter:
    def __init__(self, mode: str | None = None, fallback: FreeformProposalAdapter | None = None) -> None:
        self._mode = _resolve_freeform_mode() if mode is None else mode
        self._fallback = RuleBasedFreeformProposalAdapter() if fallback is None else fallback

    def propose(self, state: GameState, raw_input: str) -> tuple[dict[str, Any], dict[str, Any]]:
        system, user = _freeform_planner_prompt(state, raw_input)
        try:
            payload = _story_agent_json_from_text(_story_agent_chat_complete(self._mode, system, user))
            if payload is None:
                raise ValueError("planner_non_json")
            dialog_payload = parse_dialog_proposal(dict(payload.get("dialog_proposal", {})))
            action_payload = parse_action_proposal(_normalize_action_payload(dict(payload.get("action_proposal", {}))))
            arguments = dict(action_payload["arguments"])
            arguments["planner_source"] = "llm"
            action_payload["arguments"] = arguments
            return dialog_payload, action_payload
        except Exception as exc:
            dialog_payload, action_payload = self._fallback.propose(state, raw_input)
            arguments = dict(action_payload["arguments"])
            arguments["planner_source"] = "fallback"
            arguments["planner_error"] = _short_text(str(exc), 120)
            action_payload["arguments"] = arguments
            return dialog_payload, action_payload


def _dialog_line(intent: str, target: str, topic: str, state: GameState | None = None) -> str:
    speaker = target.replace("_", " ").title()
    if not target:
        if intent == "inspect":
            return "You focus on the details and search for a usable clue."
        if intent == "knock":
            return "Your knock echoes through the entryway."
        return "Only the tide answers; no one here responds to that."
    if intent == "greet":
        return f"{speaker} nods once. 'Good to see you. What do you need?'"
    if intent == "apologize":
        return f"{speaker} exhales. 'All right. Let's move forward.'"
    if intent == "threaten":
        return f"{speaker} narrows their eyes. 'Threats won't help us solve this.'"
    if topic:
        if topic == "place" and state is not None:
            room = state.world.rooms[state.player.location]
            if room.id == "front_steps":
                return (
                    f"{speaker} says, 'The mud marks are fresh, and that ledger page did not land there by accident. "
                    "This entryway is already telling us where to start.'"
                )
            if room.item_ids:
                first_item = room.item_ids[0].replace("_", " ")
                return f"{speaker} says, 'This room matters because of the {first_item}. I'd start there before we move on.'"
            exits = sorted(room.exits.keys())
            if exits:
                return f"{speaker} says, 'Nothing here feels settled. We clear this room, then push {exits[0]}.'"
            return f"{speaker} says, 'The room is thin on comfort and thick with loose ends. We should search it carefully.'"
        if topic in {"objective", "goal", "goals"} and state is not None:
            return f"{speaker} says, 'Our current objective is clear: {state.active_goal}'"
        if topic in {"appearance", "clothing", "clothes", "wearing"}:
            return (
                f"{speaker} says, 'I'm wearing a dark field coat, practical boots, and clothes meant for bad weather "
                "and worse conversations. I dressed for work, not display.'"
            )
        if topic in {"rumor", "rumors"}:
            return (
                f"{speaker} says, 'Rumors are noisy unless we anchor them. Ask about a person, item, "
                "or place, and I can give you something usable.'"
            )
        return f"{speaker} says, 'About {topic}: be specific and I'll answer what I can.'"
    return f"{speaker} studies you. 'Give me a specific question.'"


def _topic_flag_fragment(raw_topic: str) -> str:
    normalized = _TOPIC_TOKEN.sub("_", raw_topic.lower()).strip("_")
    if not normalized:
        return "rumors"
    for token in normalized.split("_"):
        if token and token not in _TOPIC_STOPWORDS:
            return token
    return "rumors"


def _apply_raw_command_overrides(
    state: GameState,
    raw_input: str,
    action_proposal: dict[str, Any],
    dialog_proposal: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    lowered = raw_input.strip().lower()
    if _CASE_FILE_COMMAND.search(lowered) and "case_file" in state.player.inventory:
        action = {
            "intent": "read_case_file",
            "targets": ["case_file"],
            "arguments": {"source_command": "read_case_file"},
            "proposed_effects": ["reviewed_case_file"],
        }
        dialog = {
            "speaker": "narrator",
            "text": "You read the case file and mark a concrete lead for your next question.",
            "tone": "in_world",
        }
        return parse_action_proposal(action), parse_dialog_proposal(dialog)
    visible_items = room_items(state, player_location(state))
    if _LEDGER_PAGE_COMMAND.search(lowered) and (
        "ledger_page" in visible_items or "ledger_page" in state.player.inventory
    ):
        action = {
            "intent": "read_ledger_page",
            "targets": ["ledger_page"],
            "arguments": {"source_command": "read_ledger_page"},
            "proposed_effects": ["reviewed_ledger_page"],
        }
        dialog = {
            "speaker": "narrator",
            "text": "You study the ledger page and pull out a useful thread: a missing payment entry tied to tonight's visit.",
            "tone": "in_world",
        }
        return parse_action_proposal(action), parse_dialog_proposal(dialog)
    return action_proposal, dialog_proposal


def _envelope_for_action(state: GameState, action_proposal: dict[str, Any]) -> dict[str, Any]:
    targets = tuple(action_proposal["targets"])
    intent = str(action_proposal["intent"]).strip().lower()
    if not intent:
        intent = "freeform"

    if intent in _ALLOWED_INTENTS and not targets:
        return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_NO_TARGET"]}

    if intent == "read_case_file":
        if "case_file" not in state.player.inventory:
            return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_MISSING_CASE_FILE"]}
        return {
            "assert": [
                {"fact": ["flag", "player", "reviewed_case_file"]},
                {"fact": ["flag", "player", "freeform_intent_read_case_file"]},
            ],
            "retract": [],
            "numeric_delta": [],
            "reasons": ["freeform:read_case_file"],
        }

    if intent == "read_ledger_page":
        visible_items = room_items(state, player_location(state))
        if "ledger_page" not in visible_items and "ledger_page" not in state.player.inventory:
            return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_MISSING_LEDGER_PAGE"]}
        return {
            "assert": [
                {"fact": ["flag", "player", "reviewed_ledger_page"]},
                {"fact": ["flag", "player", "freeform_intent_read_ledger_page"]},
            ],
            "retract": [],
            "numeric_delta": [{"key": "trust:daria_stone:player", "delta": 0.03}],
            "reasons": ["freeform:read_ledger_page"],
        }

    if not targets or intent not in _ALLOWED_INTENTS:
        normalized_intent = _topic_flag_fragment(intent)
        assert_ops: list[dict[str, Any]] = [{"fact": ["flag", "player", f"freeform_intent_{normalized_intent}"]}]
        reasons = [f"freeform:{normalized_intent}", "POLICY_GENERIC_FREEFORM"]
        if targets:
            normalized_target = _topic_flag_fragment(str(targets[0]))
            assert_ops.append({"fact": ["flag", "player", f"freeform_target_{normalized_target}"]})
        return {
            "assert": assert_ops,
            "retract": [],
            "numeric_delta": [],
            "reasons": reasons,
        }

    target = str(targets[0])
    visible_npcs = room_npcs(state, player_location(state))
    if target not in visible_npcs:
        return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_TARGET_NOT_PRESENT"]}

    reasons = [f"freeform:{intent}"]
    assert_ops: list[dict[str, Any]] = []
    numeric_delta: list[dict[str, Any]] = []
    trust_delta = 0.0

    if intent == "ask_about":
        topic = _topic_flag_fragment(action_proposal["arguments"].get("topic", "rumors"))
        if topic not in _ALLOWED_TOPIC_FLAGS:
            reasons.append("POLICY_TOPIC_BLOCKED")
        else:
            assert_ops.append({"fact": ["flag", "player", f"asked_{topic}_{target}"]})
            trust_delta = 0.05
    elif intent == "greet":
        assert_ops.append({"fact": ["flag", "player", f"greeted_{target}"]})
        trust_delta = 0.02
    elif intent == "apologize":
        assert_ops.append({"fact": ["flag", "player", f"apologized_{target}"]})
        trust_delta = 0.03
    elif intent == "threaten":
        assert_ops.append({"fact": ["flag", "player", f"threatened_{target}"]})
        trust_delta = -0.1

    if trust_delta > _PER_TURN_DELTA_BOUND:
        trust_delta = _PER_TURN_DELTA_BOUND
    if trust_delta < -_PER_TURN_DELTA_BOUND:
        trust_delta = -_PER_TURN_DELTA_BOUND
    if trust_delta != 0.0:
        numeric_delta.append({"key": f"trust:{target}:player", "delta": trust_delta})

    return {
        "assert": assert_ops,
        "retract": [],
        "numeric_delta": numeric_delta,
        "reasons": reasons,
    }


def _story_deltas_for_freeform(action_proposal: dict[str, Any], envelope: dict[str, Any]) -> tuple[float, float]:
    intent = str(action_proposal["intent"]).strip().lower()
    reasons = tuple(str(value) for value in envelope["reasons"])
    if "POLICY_TARGET_NOT_PRESENT" in reasons:
        return 0.0, 0.0
    if "POLICY_MISSING_CASE_FILE" in reasons:
        return 0.0, 0.0
    if "POLICY_MISSING_LEDGER_PAGE" in reasons:
        return 0.0, 0.0

    progress = 0.01
    tension = 0.01
    if "freeform:read_ledger_page" in reasons:
        return 0.03, 0.01
    if any(token in intent for token in _PROGRESSIVE_TOKENS):
        progress += 0.01
    if any(token in intent for token in _ESCALATION_TOKENS):
        tension += 0.04
    if "POLICY_GENERIC_FREEFORM" in reasons:
        progress += 0.005
    return progress, tension


def _envelope_to_fact_ops(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    fact_ops: list[dict[str, Any]] = []
    for mutation in envelope["assert"]:
        fact_ops.append({"op": "assert", "fact": tuple(mutation["fact"])})
    for mutation in envelope["retract"]:
        fact_ops.append({"op": "retract", "fact": tuple(mutation["fact"])})
    for metric in envelope["numeric_delta"]:
        fact_ops.append({"op": "numeric_delta", "key": metric["key"], "delta": metric["delta"]})
    return fact_ops


def _format_character_reply_line(state: GameState, dialog_proposal: dict[str, Any]) -> str:
    speaker_id = str(dialog_proposal.get("speaker", "")).strip()
    text = " ".join(str(dialog_proposal.get("text", "")).split()).strip()
    if not text:
        return ""
    if speaker_id in {"", "narrator", "player"}:
        return text

    npc = state.world.npcs.get(speaker_id)
    speaker_name = npc.name if npc is not None else speaker_id.replace("_", " ").title()
    quoted_match = _QUOTED_DIALOGUE_PATTERN.search(text)
    if '"' in text:
        double_quoted = re.search(r'"([^"]+)"', text)
        spoken = double_quoted.group(1).strip() if double_quoted is not None else text.strip(" \"'")
    elif " says, '" in text and text.endswith("'"):
        spoken = text.split(" says, '", 1)[1][:-1].strip()
    else:
        spoken = quoted_match.group(1).strip() if quoted_match is not None else text.strip(" \"'")
    if not spoken:
        spoken = text
    return f'{speaker_name} says: "{spoken}"'


def resolve_freeform_roleplay(
    state: GameState,
    raw_input: str,
    adapter: FreeformProposalAdapter,
) -> FreeformResolution:
    planning_state = state.clone()
    planning_state.turn_index += 1
    dialog_payload, action_payload = adapter.propose(planning_state, raw_input)
    return resolve_freeform_roleplay_with_proposals(state, raw_input, dialog_payload, action_payload)


def resolve_freeform_roleplay_with_proposals(
    state: GameState,
    raw_input: str,
    dialog_payload: dict[str, Any],
    action_payload: dict[str, Any],
) -> FreeformResolution:
    next_state = state.clone()
    next_state.turn_index += 1

    dialog_proposal = parse_dialog_proposal(dialog_payload)
    action_proposal = parse_action_proposal(action_payload)
    action_proposal, dialog_proposal = _apply_raw_command_overrides(
        next_state,
        raw_input,
        action_proposal,
        dialog_proposal,
    )
    envelope = parse_state_update_envelope(_envelope_for_action(next_state, action_proposal))
    if "POLICY_TARGET_NOT_PRESENT" in envelope["reasons"]:
        dialog_proposal = parse_dialog_proposal(
            {
                "speaker": "narrator",
                "text": "No one here answers that. Try speaking to someone in the room.",
                "tone": "boundary",
            }
        )

    fact_ops = _envelope_to_fact_ops(envelope)
    if fact_ops:
        apply_fact_ops(next_state, fact_ops)

    delta_progress, delta_tension = _story_deltas_for_freeform(action_proposal, envelope)
    event = Event(
        type="freeform_roleplay",
        message_key=_format_character_reply_line(next_state, dialog_proposal),
        entities=tuple(action_proposal["targets"]),
        tags=("dialog", "freeform"),
        delta_progress=delta_progress,
        delta_tension=delta_tension,
        turn_index=next_state.turn_index,
        metadata={
            "action_proposal": action_proposal,
            "dialog_proposal": dialog_proposal,
            "state_update_envelope": envelope,
            "fact_ops": fact_ops,
        },
    )
    next_state.append_event(event)
    next_state.progress = max(0.0, min(1.0, next_state.progress + delta_progress))
    next_state.tension = max(0.0, min(1.0, next_state.tension + delta_tension))
    return {
        "state": next_state,
        "event": event,
        "action_proposal": action_proposal,
        "dialog_proposal": dialog_proposal,
        "state_update_envelope": envelope,
    }

DEFAULT_FREEFORM_ADAPTER = LlmFreeformProposalAdapter()
