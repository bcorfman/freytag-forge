from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol, TypedDict

from storygame.engine.facts import active_story_goal, player_location, protagonist_profile, room_items, room_npcs
from storygame.engine.interfaces import parse_action_proposal, parse_dialog_proposal, parse_state_update_envelope
from storygame.engine.parser import ActionKind, parse_command
from storygame.engine.scene_state import refresh_scene_state
from storygame.engine.state import Event, GameState
from storygame.engine.turn_runtime import execute_turn_proposal
from storygame.llm.contracts import parse_turn_proposal
from storygame.llm.story_agents.agents import _chat_complete as _story_agent_chat_complete
from storygame.llm.story_agents.agents import _json_from_text as _story_agent_json_from_text
from storygame.plot.dramatic_policy import turn_focus_from_freeform

_TOPIC_TOKEN = re.compile(r"[^a-z0-9]+")
_ASK_TARGET_PATTERN = re.compile(r"\bask\s+([a-z0-9_ .'-]{1,60}?)(?:\s+about\b|$)", re.IGNORECASE)
_DIRECT_ADDRESS_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z .'-]{0,60})\s*,")
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
_PLAYER_APPEARANCE_QUESTION_PATTERN = re.compile(r"\bwhat am i wearing\b", re.IGNORECASE)
_REMOVE_COAT_REQUEST_PATTERN = re.compile(r"\b(take off|remove)\s+(?:your\s+)?coat\b", re.IGNORECASE)
_SERVICE_PASSAGE_PATTERN = re.compile(r"\bservice\s+passage\b", re.IGNORECASE)
_SERVICE_PASSAGE_LOCATION_PATTERN = re.compile(
    r"\b(where is|where's|located|location|take me to|show me|lead me to|how do we get to)\b",
    re.IGNORECASE,
)
_ROUTE_KEY_PATTERN = re.compile(r"\broute\s+key\b|\bkey\b", re.IGNORECASE)
_CONVERSATIONAL_WORD_PATTERN = re.compile(r"\b(ask|tell|say|speak|talk|hello|hi|who|what|where|why|how)\b", re.IGNORECASE)
_HIDDEN_FREEFORM_MESSAGE_KEYS = {
    "query",
    "ask_about",
    "greet",
    "apologize",
    "threaten",
    "inspect",
    "knock",
}


def _short_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _clean_topic_text(value: str) -> str:
    cleaned = value.strip().strip(" ,.;:!?")
    normalized = _normalize_target(cleaned)
    tokens = [token for token in normalized.split("_") if token and token not in _TOPIC_STOPWORDS]
    return " ".join(tokens).strip()


def _is_conversational_input(raw_input: str, first_word: str, explicit_target_requested: bool) -> bool:
    if explicit_target_requested:
        return True
    if first_word in {"talk", "speak", "speak_to", "speakto", "hello", "hi", "greet", "ask", "tell"}:
        return True
    return _CONVERSATIONAL_WORD_PATTERN.search(raw_input) is not None


def _topic_from_raw_input(raw_input: str, text: str) -> str:
    if _REMOVE_COAT_REQUEST_PATTERN.search(raw_input):
        return "remove coat request"
    if _PLAYER_APPEARANCE_QUESTION_PATTERN.search(raw_input):
        return "player appearance"
    if _SERVICE_PASSAGE_PATTERN.search(raw_input):
        if _SERVICE_PASSAGE_LOCATION_PATTERN.search(raw_input):
            return "service passage location"
        return "service passage"
    if _ROUTE_KEY_PATTERN.search(raw_input):
        return "route key"
    if _APPEARANCE_QUESTION_PATTERN.search(raw_input):
        return "appearance"
    if re.search(r"\b(goal|goals|objective|objectives)\b", text):
        return "objective"
    if "about" in text:
        return _clean_topic_text(text.split("about", 1)[1]) or "rumors"
    if _PLACE_QUESTION_PATTERN.search(raw_input):
        return "place"
    return "rumors"


class FreeformProposalAdapter(Protocol):
    def propose(self, state: GameState, raw_input: str) -> tuple[dict[str, Any], dict[str, Any]]: ...


class FreeformResolution(TypedDict):
    state: GameState
    events: list[Event]
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
        if (
            not target
            and visible_npcs
            and not explicit_target_requested
            and _is_conversational_input(raw_input, first, explicit_target_requested)
        ):
            target = visible_npcs[0]

        intent = "ask_about"
        topic = "rumors"
        if conversation_head:
            intent = "greet"
            topic = ""
            if "about" in text:
                intent = "ask_about"
                topic = _clean_topic_text(text.split("about", 1)[1]) or "rumors"
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
        else:
            topic = _topic_from_raw_input(raw_input, text)

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
        response = _dialog_line(intent=intent, target=target, topic=topic, state=state)
        if explicit_target_requested and not target:
            response = "No one here answers that. Try speaking to someone in the room."
        dialog_payload = {"speaker": "narrator", "text": response, "tone": "in_world"}
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


def _find_relevant_item(state: GameState, raw_topic: str) -> str:
    topic = _normalize_target(raw_topic)
    if not topic:
        return ""

    room = state.world.rooms[state.player.location]
    candidate_item_ids = tuple(dict.fromkeys((*state.player.inventory, *room.item_ids)))
    for item_id in candidate_item_ids:
        if item_id == topic or topic in item_id:
            return item_id
        item = state.world.items.get(item_id)
        if item is None:
            continue
        normalized_name = _normalize_target(item.name)
        if normalized_name == topic or topic in normalized_name:
            return item_id
        if any(part and part == topic for part in normalized_name.split("_")):
            return item_id
    return ""


def _nearby_holder_for_item(state: GameState, item_id: str) -> str:
    room_id = player_location(state)
    for npc_id in room_npcs(state, room_id):
        if state.world_facts.holds("holding", npc_id, item_id):
            return npc_id
    return ""


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
        "goal": active_story_goal(state),
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
        "For uncertain targets, use an empty targets list and a generic intent. "
        "If the player clearly addresses or questions a visible NPC, dialog_proposal.speaker must be that NPC and "
        "dialog_proposal.text must be the NPC's in-character reply, not the player's line and not narrator summary."
    )
    return system, json.dumps(payload, ensure_ascii=True)


def _normalize_action_payload(action_payload: dict[str, Any]) -> dict[str, Any]:
    intent = _normalize_target(str(action_payload.get("intent", "")))
    targets = [_normalize_target(str(target)) for target in action_payload.get("targets", [])]
    raw_arguments = action_payload.get("arguments", {})
    arguments = (
        {str(k): str(v) for k, v in raw_arguments.items()}
        if isinstance(raw_arguments, dict)
        else {}
    )
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
        self._fallback = fallback

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
            if self._fallback is not None:
                dialog_payload, action_payload = self._fallback.propose(state, raw_input)
                arguments = dict(action_payload["arguments"])
                arguments["planner_source"] = "fallback"
                arguments["planner_error"] = _short_text(str(exc), 120)
                action_payload["arguments"] = arguments
                return dialog_payload, action_payload
            raise RuntimeError(f"FREEFORM_PLANNER_UNAVAILABLE: {_short_text(str(exc), 120)}") from exc


def _dialog_line(intent: str, target: str, topic: str, state: GameState | None = None) -> str:
    speaker = target.replace("_", " ").title()
    if not target:
        if intent == "inspect":
            return "You focus on the details and search for a usable clue."
        if intent == "knock":
            return "Your knock echoes through the entryway."
        return "You leave the remark hanging in the room with no clear respondent."
    if intent == "greet":
        return f"You greet {speaker} and wait for the conversation to start."
    if intent == "apologize":
        return f"You apologize to {speaker} and watch for any shift in the mood."
    if intent == "threaten":
        return f"You put pressure on {speaker}, testing how far the exchange will bend."
    if topic:
        if topic == "player appearance":
            return f"You ask {speaker} to size up your appearance and wait for the answer."
        if topic == "remove coat request":
            return f"You press {speaker} to remove part of their outfit and wait to see how they respond."
        if topic in {"service passage", "service passage location"}:
            return f"You ask {speaker} about the service passage and hold on the implication of a hidden route."
        if topic == "route key":
            return f"You ask {speaker} about the route key and wait for its importance to become clear."
        if state is not None:
            relevant_item_id = _find_relevant_item(state, topic)
            if relevant_item_id:
                item = state.world.items[relevant_item_id]
                item_name = item.name.lower()
                if item.clue_text:
                    return f"You ask {speaker} about the {item_name}, especially what it implies for the case."
                return f"You ask {speaker} about the {item_name} and wait for a useful read on it."
        if topic == "place" and state is not None:
            room = state.world.rooms[state.player.location]
            if room.id == "front_steps":
                return f"You ask {speaker} what they make of the front steps and the signs the weather has not erased."
            if room.item_ids:
                first_item = room.item_ids[0].replace("_", " ")
                return f"You ask {speaker} what stands out here, with the {first_item} already drawing attention."
            exits = sorted(room.exits.keys())
            if exits:
                return f"You ask {speaker} what this room suggests before either of you pushes {exits[0]}."
            return f"You ask {speaker} for a read on the room and hold on the details that matter."
        if topic in {"objective", "goal", "goals"} and state is not None:
            return f"You check the objective with {speaker}: {active_story_goal(state)}"
        if topic in {"appearance", "clothing", "clothes", "wearing"}:
            return f"You ask {speaker} about their appearance and wait for the answer."
        if topic in {"rumor", "rumors"}:
            return f"You ask {speaker} for anything useful that has been going around."
        return f"You ask {speaker} about {topic} and wait for the reply."
    return f"You turn to {speaker}, but the exchange needs a more specific question."


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
    nearby_ledger_holder = _nearby_holder_for_item(state, "ledger_page")
    if _LEDGER_PAGE_COMMAND.search(lowered) and (
        "ledger_page" in visible_items or "ledger_page" in state.player.inventory or nearby_ledger_holder
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
                {"fact": ["discovered_clue", "case_file"]},
                {"fact": ["discovered_lead", "case_file", "The case file pins down the victim timeline and highlights the first credible lead."]},
            ],
            "retract": [],
            "numeric_delta": [],
            "reasons": ["freeform:read_case_file"],
        }

    if intent == "read_ledger_page":
        visible_items = room_items(state, player_location(state))
        nearby_holder = _nearby_holder_for_item(state, "ledger_page")
        if "ledger_page" not in visible_items and "ledger_page" not in state.player.inventory and not nearby_holder:
            return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_MISSING_LEDGER_PAGE"]}
        assert_ops = [
            {"fact": ["flag", "player", "reviewed_ledger_page"]},
            {"fact": ["flag", "player", "freeform_intent_read_ledger_page"]},
            {"fact": ["discovered_clue", "ledger_page"]},
            {
                "fact": [
                    "discovered_lead",
                    "ledger_page",
                    "The ledger page exposes a missing payment entry tied to tonight's visit.",
                ]
            },
        ]
        if nearby_holder:
            assert_ops.append({"fact": ["reviewed_with_holder", nearby_holder, "ledger_page"]})
        return {
            "assert": assert_ops,
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
    if "POLICY_NO_TARGET" in reasons:
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


def _envelope_with_story_deltas(action_proposal: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    progress_delta, tension_delta = _story_deltas_for_freeform(action_proposal, envelope)
    numeric_delta = list(envelope["numeric_delta"])
    if progress_delta != 0.0:
        numeric_delta.append({"key": "progress", "delta": progress_delta})
    if tension_delta != 0.0:
        numeric_delta.append({"key": "tension", "delta": tension_delta})
    return {
        "assert": list(envelope["assert"]),
        "retract": list(envelope["retract"]),
        "numeric_delta": numeric_delta,
        "reasons": list(envelope["reasons"]),
    }


def _envelope_to_fact_ops(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    fact_ops: list[dict[str, Any]] = []
    for mutation in envelope["assert"]:
        fact_ops.append({"op": "assert", "fact": tuple(mutation["fact"])})
    for mutation in envelope["retract"]:
        fact_ops.append({"op": "retract", "fact": tuple(mutation["fact"])})
    for metric in envelope["numeric_delta"]:
        fact_ops.append({"op": "numeric_delta", "key": metric["key"], "delta": metric["delta"]})
    return fact_ops


def _semantic_actions_for_freeform(
    state: GameState,
    action_proposal: dict[str, Any],
    envelope: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    intent = str(action_proposal["intent"]).strip().lower()
    targets = tuple(str(target) for target in action_proposal["targets"])
    if "POLICY_TARGET_NOT_PRESENT" in tuple(str(reason) for reason in envelope["reasons"]):
        return ()

    if intent == "read_case_file":
        return (
            {
                "action_id": "freeform-read-case-file",
                "action_type": "inspect_item",
                "actor_id": "player",
                "target_id": "",
                "item_id": "case_file",
                "location_id": player_location(state),
            },
        )
    if intent == "read_ledger_page":
        return (
            {
                "action_id": "freeform-read-ledger-page",
                "action_type": "inspect_item",
                "actor_id": "player",
                "target_id": "",
                "item_id": "ledger_page",
                "location_id": player_location(state),
            },
        )
    if intent in _ALLOWED_INTENTS and targets:
        return (
            {
                "action_id": f"freeform-{intent}",
                "action_type": intent,
                "actor_id": "player",
                "target_id": targets[0],
                "item_id": "",
                "location_id": player_location(state),
            },
        )
    if intent:
        return (
            {
                "action_id": f"freeform-{intent}",
                "action_type": intent,
                "actor_id": "player",
                "target_id": targets[0] if targets else "",
                "item_id": "",
                "location_id": player_location(state),
            },
        )
    return ()


def _format_character_reply_line(
    state: GameState,
    dialog_proposal: dict[str, Any],
    action_proposal: dict[str, Any],
) -> str:
    speaker_id = str(dialog_proposal.get("speaker", "")).strip()
    text = " ".join(str(dialog_proposal.get("text", "")).split()).strip()
    if not text:
        return ""
    normalized_speaker = _normalized_dialog_speaker_id(state, speaker_id, action_proposal)
    if normalized_speaker in {"", "narrator"}:
        return text
    if normalized_speaker == "player":
        return f'{_player_speaker_name(state)} says: "{text.strip(" \"\'")}"'

    npc = state.world.npcs.get(normalized_speaker)
    speaker_name = npc.name if npc is not None else normalized_speaker.replace("_", " ").title()
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


def _player_speaker_name(state: GameState) -> str:
    profile_name = protagonist_profile(state).get("name", "").strip()
    if profile_name:
        cleaned = profile_name.removeprefix("Detective ").strip()
        return cleaned.split(" ")[0] if cleaned else "You"
    return "You"


def _normalized_dialog_speaker_id(state: GameState, speaker_id: str, action_proposal: dict[str, Any]) -> str:
    normalized = _normalize_target(speaker_id)
    if normalized in {"", "narrator"}:
        return "narrator"
    if normalized in {"player", "you", "user", "detective", "detective_elias_wren", "elias", "elias_wren"}:
        return "player"
    if normalized in state.world.npcs:
        return normalized
    matched_npc = _visible_npc_match(state, speaker_id)
    if matched_npc:
        return matched_npc
    if normalized in {"ai_assistant", "assistant"}:
        targets = action_proposal.get("targets", ())
        if isinstance(targets, (list, tuple)):
            for target in targets:
                candidate = _normalize_target(str(target))
                if candidate in state.world.npcs:
                    return candidate
    return normalized or "narrator"


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
    dialog_proposal = parse_dialog_proposal(dialog_payload)
    action_proposal = parse_action_proposal(action_payload)
    action_proposal, dialog_proposal = _apply_raw_command_overrides(
        state,
        raw_input,
        action_proposal,
        dialog_proposal,
    )
    envelope = parse_state_update_envelope(_envelope_for_action(state, action_proposal))
    if "POLICY_TARGET_NOT_PRESENT" in envelope["reasons"]:
        dialog_proposal = parse_dialog_proposal(
            {
                "speaker": "narrator",
                "text": "No one here answers that. Try speaking to someone in the room.",
                "tone": "boundary",
            }
        )
    envelope = parse_state_update_envelope(_envelope_with_story_deltas(action_proposal, envelope))

    turn_proposal = parse_turn_proposal(
        {
            "turn_id": f"freeform-{state.turn_index + 1}",
            "mode": "conversation" if action_proposal["targets"] else "scene",
            "player_intent": {
                "summary": str(action_proposal["intent"]),
                "addressed_npc_id": str(action_proposal["targets"][0]) if action_proposal["targets"] else "",
                "target_ids": tuple(str(target) for target in action_proposal["targets"]),
                "item_ids": (),
                "location_id": player_location(state),
            },
            "scene_framing": {
                "focus": str(action_proposal["arguments"].get("topic", "")),
                "dramatic_question": "",
                "player_approach": "",
            },
            "npc_dialogue": {
                "speaker_id": _normalized_dialog_speaker_id(state, str(dialog_proposal.get("speaker", "")), action_proposal),
                "text": str(dialog_proposal["text"]),
            },
            "narration": str(dialog_proposal["text"]),
            "semantic_actions": _semantic_actions_for_freeform(state, action_proposal, envelope),
            "state_delta": envelope,
            "beat_hints": {
                "escalation": "none",
                "reveal_thread_ids": (),
                "obstacle_mode": "",
            },
        }
    )
    runtime_result = execute_turn_proposal(state, turn_proposal, None)
    next_state = runtime_result["state"]
    committed_events = list(runtime_result["events"])
    committed_fact_ops: list[dict[str, Any]] = _envelope_to_fact_ops(envelope)
    for committed_event in committed_events:
        fact_ops = committed_event.metadata.get("fact_ops", ())
        if isinstance(fact_ops, (list, tuple)):
            committed_fact_ops.extend(dict(op) for op in fact_ops)
        numeric_delta = committed_event.metadata.get("numeric_delta", ())
        if isinstance(numeric_delta, (list, tuple)):
            committed_fact_ops.extend({"op": "numeric_delta", "key": entry["key"], "delta": entry["delta"]} for entry in numeric_delta)

    delta_progress = max(0.0, next_state.progress - state.progress)
    delta_tension = max(0.0, next_state.tension - state.tension)
    compatibility_event = Event(
        type="freeform_roleplay",
        message_key=_format_character_reply_line(next_state, dialog_proposal, action_proposal),
        entities=tuple(action_proposal["targets"]),
        tags=("dialog", "freeform"),
        delta_progress=delta_progress,
        delta_tension=delta_tension,
        turn_index=next_state.turn_index,
        metadata={
            "action_proposal": action_proposal,
            "dialog_proposal": dialog_proposal,
            "state_update_envelope": envelope,
            "fact_ops": committed_fact_ops,
            "committed_event_types": [event.type for event in committed_events],
        },
    )
    next_state.append_event(compatibility_event)
    committed_events.append(compatibility_event)
    refresh_scene_state(next_state, turn_focus_from_freeform(next_state, action_proposal))
    return {
        "state": next_state,
        "events": committed_events,
        "event": compatibility_event,
        "action_proposal": action_proposal,
        "dialog_proposal": dialog_proposal,
        "state_update_envelope": envelope,
    }

DEFAULT_FREEFORM_ADAPTER = LlmFreeformProposalAdapter()
