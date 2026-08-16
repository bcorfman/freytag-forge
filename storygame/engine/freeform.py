# ruff: noqa: E501

from __future__ import annotations

import json
import re
from typing import Any, Protocol, TypedDict

from storygame.engine.facts import (
    active_story_goal,
    item_driver,
    item_owner,
    item_state,
    npc_scene_purpose,
    player_context_facts,
    player_location,
    protagonist_profile,
    room_items,
    room_npcs,
)
from storygame.engine.interfaces import parse_action_proposal, parse_dialog_proposal, parse_state_update_envelope
from storygame.engine.perception import observer_context_slice, speaker_context_slice
from storygame.engine.presentation import npc_reference_name
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
_DOUBLE_QUOTED_DIALOGUE_PATTERN = re.compile(r'"([^"]+)"')
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
_CONVERSATIONAL_WORD_PATTERN = re.compile(
    r"\b(ask|tell|say|speak|talk|hello|hi|who|what|where|why|how)\b", re.IGNORECASE
)
_MOVEMENT_PHRASE_PATTERN = re.compile(
    r"\b(enter|head|go|walk|step|move|return|back|inside|outside|indoors|outdoors|door|entrance|exit)\b",
    re.IGNORECASE,
)
_TAKE_REQUEST_PATTERN = re.compile(r"\b(?:take|get|grab|acquire|pick\s+up)\b", re.IGNORECASE)
_HIDDEN_FREEFORM_MESSAGE_KEYS = {
    "query",
    "ask_about",
    "greet",
    "apologize",
    "threaten",
    "inspect",
    "knock",
}
_EXPLICIT_CONVERSATION_HEADS = {"talk", "speak", "speak_to", "speakto", "ask", "tell", "say", "hello", "hi", "greet"}
_LOW_SIGNAL_PLAYER_ECHO_PATTERN = re.compile(
    r"^[\"']?\s*(?:open|close|get|take|use|inspect|examine|look|go|enter)\b", re.IGNORECASE
)
_CODE_ARTIFACT_TOKEN_PATTERN = re.compile(r"\b[a-z]+(?:[A-Z][a-z0-9]+){1,}\b")
_PLANNER_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "can",
    "did",
    "do",
    "give",
    "me",
    "of",
    "on",
    "the",
    "to",
    "was",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
    "you",
    "your",
}
_PLANNER_BROAD_FACT_TERMS = {
    "brief",
    "case",
    "clue",
    "happened",
    "incident",
    "situation",
    "timeline",
    "victim",
    "witness",
}


def _short_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _planner_query_tokens(raw_input: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", raw_input.lower())
        if token not in _PLANNER_STOPWORDS and len(token) > 2
    }


def _planner_fact_text(entry: object) -> str:
    if isinstance(entry, dict):
        return " ".join(f"{key} {value}" for key, value in entry.items())
    return str(entry)


def _planner_relevant_facts(entries: list[object], query_tokens: set[str], broad: bool) -> list[object]:
    if broad:
        return entries[-8:]
    return [entry for entry in entries if query_tokens.intersection(_planner_query_tokens(_planner_fact_text(entry)))]


def is_player_statement_echo(raw_input: str, player_facing_text: str) -> bool:
    """Identify a response that contributes nothing beyond the player's words."""
    normalized_input = " ".join(re.findall(r"[a-z0-9]+", raw_input.lower()))
    normalized_output = " ".join(re.findall(r"[a-z0-9]+", player_facing_text.lower()))
    return bool(normalized_input) and normalized_output == normalized_input


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


def _explicit_npc_address_requested(raw_input: str) -> bool:
    stripped = raw_input.strip()
    if not stripped:
        return False
    if _DIRECT_ADDRESS_PATTERN.match(stripped):
        return True
    if _ASK_TARGET_PATTERN.search(stripped):
        return True
    words = stripped.lower().split()
    if not words:
        return False
    return words[0] in _EXPLICIT_CONVERSATION_HEADS


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


class OrdinaryTurnRecoveryExhausted(RuntimeError):
    """Fail-closed result when the ordinary planner has used its one retry."""

    code = "ORDINARY_TURN_RECOVERY_EXHAUSTED"
    attempts = 2
    budget = 2

    def __init__(self, cause: Exception) -> None:
        self.cause = _short_text(str(cause), 120)
        super().__init__(f"{self.code}: {self.cause}")


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
        semantic_move_direction = _semantic_exit_direction(state, raw_input)
        if semantic_move_direction:
            return (
                {
                    "speaker": "narrator",
                    "text": "You commit to the nearest clear route and move through it.",
                    "tone": "in_world",
                },
                {
                    "intent": "move",
                    "targets": [semantic_move_direction],
                    "arguments": {"semantic_navigation": "true"},
                    "proposed_effects": [f"move:{semantic_move_direction}"],
                },
            )

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
                if any(
                    name_part and name_part in text
                    for name_part in (_normalize_target(part) for part in npc.name.split())
                ):
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
        if re.search(r"\b(look|examine|inspect|read|review)\b", text):
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
            readable_item = _readable_item_for_input(state, raw_input)
            targets = [readable_item] if readable_item else []

        action_payload = {
            "intent": intent,
            "targets": targets,
            "arguments": {"topic": topic} if topic else {},
            "proposed_effects": [f"{intent}:{targets[0] if targets else 'none'}"],
        }
        response = _dialog_line(intent=intent, target=target, topic=topic, state=state)
        document_reveals = _document_reveal_facts_for_input(state, raw_input)
        if document_reveals:
            revealed_values = "; ".join(str(reveal["value"]) for reveal in document_reveals)
            response = f"The document fixes new points: {revealed_values}"
        if explicit_target_requested and not target:
            response = "No one here answers that. Try speaking to someone in the room."
        dialog_payload = {"speaker": "narrator", "text": response, "tone": "in_world"}
        return dialog_payload, action_payload


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


def _readable_item_for_input(state: GameState, raw_input: str) -> str:
    """Resolve one currently accessible readable item from fact-backed aliases."""
    normalized = f" {_normalize_target(raw_input).replace('_', ' ')} "
    accessible = set(state.player.inventory) | set(room_items(state, player_location(state)))
    accessible.update(item_id for item_id in state.world.items if _nearby_holder_for_item(state, item_id))
    matches = [
        item_id
        for item_id in sorted(accessible)
        if state.world_facts.holds("item_affordance", item_id, "read")
        and any(
            f" {str(fact[2]).lower()} " in normalized for fact in state.world_facts.query("item_alias", item_id, None)
        )
    ]
    return matches[0] if len(matches) == 1 else ""


def _takeable_item_for_input(state: GameState, raw_input: str) -> str:
    """Resolve one explicit pickup request against visible, portable item aliases."""
    if _explicit_npc_address_requested(raw_input) or not _TAKE_REQUEST_PATTERN.search(raw_input):
        return ""
    normalized = f" {_normalize_target(raw_input).replace('_', ' ')} "
    matches: list[str] = []
    for item_id in room_items(state, player_location(state)):
        item = state.world.items.get(item_id)
        if item is None or not item.portable:
            continue
        aliases = [item_id.replace("_", " "), item.name]
        aliases.extend(str(fact[2]) for fact in state.world_facts.query("item_alias", item_id, None))
        if any(f" {alias.lower().strip()} " in normalized for alias in aliases if alias.strip()):
            matches.append(item_id)
    return matches[0] if len(matches) == 1 else ""


def _movement_requested(raw_input: str) -> bool:
    return _MOVEMENT_PHRASE_PATTERN.search(raw_input) is not None


def _room_environment(room) -> str:  # noqa: ANN001
    """Presentation-derived compatibility label; navigation itself uses exits."""
    text = f" {room.id.replace('_', ' ')} {room.name.lower()} {room.description.lower()} "
    if any(token in text for token in (" outside ", " steps ", " street ", " lane ", " road ", " trail ")):
        return "outdoor"
    if any(token in text for token in (" foyer ", " hall ", " office ", " room ", " chamber ", " interior ")):
        return "indoor"
    return "unknown"


def _exit_match_score(
    state: GameState,
    raw_input: str,
    direction: str,
    destination_room_id: str,
) -> int:
    text = f" {_normalize_target(raw_input).replace('_', ' ')} "
    destination_room = state.world.rooms[destination_room_id]
    score = 0

    if destination_room.name and destination_room.name.lower() in text:
        score += 8
    destination_id_text = destination_room_id.replace("_", " ")
    if destination_id_text in text:
        score += 7
    if any(
        f" {str(fact[3]).lower()} " in text
        for fact in state.world_facts.query("path_alias", state.player.location, direction, None)
    ):
        score += 9
    inward_request = any(phrase in text for phrase in (" enter ", " inside ", " into ", " head in ", " go in "))
    outward_request = any(phrase in text for phrase in (" outside ", " back outside ", " back out ", " leave "))
    if _room_environment(destination_room) == "indoor" and inward_request:
        score += 4
    if _room_environment(destination_room) == "outdoor" and outward_request:
        score += 4

    return score


def _semantic_exit_direction(state: GameState, raw_input: str) -> str:
    if _explicit_npc_address_requested(raw_input):
        return ""
    if not _movement_requested(raw_input):
        return ""
    room = state.world.rooms[state.player.location]
    if not room.exits:
        return ""
    if len(room.exits) == 1 and any(token in raw_input.lower() for token in ("enter", "inside", "door", "entrance")):
        return next(iter(room.exits.values()))
    scored: list[tuple[int, str]] = []
    for direction, destination_room_id in room.exits.items():
        score = _exit_match_score(state, raw_input, direction, destination_room_id)
        if score > 0:
            scored.append((score, direction))
    if not scored:
        return ""
    scored.sort(reverse=True)
    best_score, best_direction = scored[0]
    if len(scored) > 1 and scored[1][0] == best_score:
        return ""
    return room.exits[best_direction] if best_score > 0 else ""


def _normalized_movement_action_payload(
    state: GameState, raw_input: str, action_payload: dict[str, Any]
) -> dict[str, Any]:
    take_item = _takeable_item_for_input(state, raw_input)
    if take_item:
        normalized = dict(action_payload)
        normalized["intent"] = "take"
        normalized["targets"] = [take_item]
        arguments = dict(normalized.get("arguments", {}))
        arguments.setdefault("deterministic_affordance", "take")
        normalized["arguments"] = arguments
        normalized["proposed_effects"] = [f"take:{take_item}"]
        return normalized

    intent = str(action_payload.get("intent", "")).strip().lower()
    targets = [str(target) for target in action_payload.get("targets", ())]
    move_direction = _semantic_exit_direction(state, raw_input)
    if not move_direction:
        return action_payload
    if _movement_requested(raw_input) or intent in {"", "freeform", "move", "go", "walk", "travel", "head", "enter"}:
        normalized = dict(action_payload)
        normalized["intent"] = "move"
        normalized["targets"] = [move_direction]
        arguments = dict(normalized.get("arguments", {}))
        arguments.setdefault("semantic_navigation", "true")
        normalized["arguments"] = arguments
        normalized["proposed_effects"] = [f"move:{move_direction}"]
        return normalized
    room = state.world.rooms[state.player.location]
    if intent in {"move", "go", "walk", "travel"} and targets and targets[0] not in room.exits:
        normalized = dict(action_payload)
        normalized["targets"] = [move_direction]
        normalized["proposed_effects"] = [f"move:{move_direction}"]
        return normalized
    return action_payload


def _nearby_holder_for_item(state: GameState, item_id: str) -> str:
    room_id = player_location(state)
    for npc_id in room_npcs(state, room_id):
        if state.world_facts.holds("holding", npc_id, item_id):
            return npc_id
    return ""


def _document_reveal_facts_for_input(state: GameState, raw_input: str) -> list[dict[str, str]]:
    """Expose declared document facts only while planning that document's read."""
    if not re.search(r"\b(read|review|examine|inspect)\b", raw_input, re.IGNORECASE):
        return []
    item_id = _readable_item_for_input(state, raw_input)
    if not item_id:
        return []
    visible_items = room_items(state, player_location(state))
    if (
        item_id not in state.player.inventory
        and item_id not in visible_items
        and not _nearby_holder_for_item(state, item_id)
    ):
        return []
    case_values = {fact[1]: fact[2] for fact in state.world_facts.query("case_fact", None, None)}
    return [
        {"key": fact[2], "value": case_values[fact[2]]}
        for fact in state.world_facts.query("document_knowledge", item_id, None)
        if fact[2] in case_values and not state.world_facts.holds("knows", "player", fact[2])
    ]


def _dialogue_conflicts_with_held_item_custody(state: GameState, text: str) -> bool:
    """Reject prose that places a fact-held item unattended in the scene."""
    lowered = " ".join(text.lower().split())
    exposed_location = r"(?:on (?:the )?(?:ground|floor|front steps|steps)|at (?:your )?feet|in (?:the )?mud|out in (?:the )?open|beside (?:the )?\w+|wedged|lodged|lying|rests?|resting)"
    for fact in state.world_facts.query("holding", None, None):
        if len(fact) != 3:
            continue
        item_id = fact[2]
        item = state.world.items.get(item_id)
        labels = {item_id.replace("_", " ")}
        if item is not None and item.name.strip():
            labels.add(item.name.lower())
        for label in labels:
            if re.search(rf"\b{re.escape(label)}\b[^.!?]{{0,100}}\b{exposed_location}\b", lowered):
                return True
    return False


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


def _addressed_visible_npc_id(state: GameState, raw_input: str) -> str:
    direct_match = _DIRECT_ADDRESS_PATTERN.match(raw_input)
    ask_match = _ASK_TARGET_PATTERN.search(raw_input)
    candidate = direct_match.group(1) if direct_match is not None else ask_match.group(1) if ask_match else ""
    return _visible_npc_match(state, candidate.strip()) if candidate else ""


def addressed_visible_npc_id(state: GameState, raw_input: str) -> str:
    """Resolve a direct player address to its visible NPC, if any."""
    return _addressed_visible_npc_id(state, raw_input)


def bind_direct_npc_conversation_target(
    state: GameState, raw_input: str, action_payload: dict[str, Any]
) -> dict[str, Any]:
    """Keep a direct NPC question's action target aligned with its reply speaker."""
    addressed_npc_id = addressed_visible_npc_id(state, raw_input)
    if not addressed_npc_id:
        return action_payload
    normalized = dict(action_payload)
    normalized["targets"] = [addressed_npc_id]
    return normalized


def _required_document_disclosure(state: GameState, raw_input: str, action_payload: dict[str, Any]) -> str:
    item_id = _readable_item_for_input(state, raw_input)
    targets = tuple(str(target) for target in action_payload.get("targets", ()))
    if not item_id or not targets:
        return ""
    speaker_id = targets[0]
    return next(
        (
            fact[3]
            for fact in state.world_facts.query("document_disclosure", item_id, speaker_id, None)
            if not state.world_facts.holds("knows", "player", fact[3])
        ),
        "",
    )


def _freeform_planner_prompt(state: GameState, raw_input: str) -> tuple[str, str]:
    room = state.world.rooms[state.player.location]
    query_tokens = _planner_query_tokens(raw_input)
    broad_fact_request = bool(query_tokens.intersection(_PLANNER_BROAD_FACT_TERMS))
    npc_facts = [
        {
            "id": npc_id,
            "name": state.world.npcs[npc_id].name,
            "identity": state.world.npcs[npc_id].identity,
            "description": state.world.npcs[npc_id].description,
            "appearance": state.world.npcs[npc_id].appearance,
            "scene_purpose": npc_scene_purpose(state, npc_id),
        }
        for npc_id in room.npc_ids
        if npc_id in state.world.npcs
    ]
    item_facts = [
        {
            "id": item_id,
            "name": state.world.items[item_id].name,
            "description": state.world.items[item_id].description,
            "kind": state.world.items[item_id].kind,
            "portable": state.world.items[item_id].portable,
            "owner": item_owner(state, item_id),
            "driver": item_driver(state, item_id),
            "state": item_state(state, item_id),
        }
        for item_id in room.item_ids
        if item_id in state.world.items
    ]
    scene_entries = [entry["text"] for entry in player_context_facts(state) if str(entry["text"]).strip()]
    permitted_player_facts = observer_context_slice(state, "player")
    case_entries = [
        {"key": fact[1], "value": fact[2]}
        for fact in permitted_player_facts
        if fact[0] == "case_fact" and len(fact) == 3
    ]
    relevant_npc_facts = [
        fact
        for fact in npc_facts
        if query_tokens.intersection(_planner_query_tokens(str(fact["name"])))
        or query_tokens.intersection(_planner_query_tokens(str(fact["identity"])))
    ]
    relevant_item_facts = [
        fact for fact in item_facts if query_tokens.intersection(_planner_query_tokens(str(fact["name"])))
    ]
    movement_request = bool(query_tokens.intersection(_MOVEMENT_PHRASE_PATTERN.findall(raw_input.lower())))
    addressed_npc_id = _addressed_visible_npc_id(state, raw_input)
    speaker_facts = (
        tuple(
            fact
            for fact in speaker_context_slice(state, addressed_npc_id)
            if fact[0] in {"knows", "believes", "suspects", "conceals", "may_infer", "case_fact"}
        )
        if addressed_npc_id
        else ()
    )
    payload = {
        "player_input": raw_input,
        "goal": _short_text(active_story_goal(state), 240),
        "turn_index": state.turn_index,
        "scene_facts": _planner_relevant_facts(scene_entries, query_tokens, broad_fact_request),
        "case_facts": _planner_relevant_facts(case_entries, query_tokens, broad_fact_request),
        "document_reveal_facts": _document_reveal_facts_for_input(state, raw_input),
        "room": {
            "id": room.id,
            "name": room.name,
            "description": _short_text(room.description, 320),
            "visible_npc_ids": list(room.npc_ids),
            "visible_item_names": [str(fact["name"]).strip() for fact in item_facts if str(fact["name"]).strip()],
            "visible_items": relevant_item_facts,
            "exits": [
                next(
                    (
                        str(fact[3])
                        for fact in state.world_facts.query("path_label", state.player.location, route_id, None)
                    ),
                    route_id.replace("_", " "),
                )
                for route_id in sorted(room.exits)
            ],
            "exit_facts": [
                {
                    "label": next(
                        (
                            str(fact[3])
                            for fact in state.world_facts.query("path_label", state.player.location, route_id, None)
                        ),
                        route_id.replace("_", " "),
                    ),
                    "destination_name": state.world.rooms[destination].name,
                }
                for route_id, destination in sorted(room.exits.items())
            ]
            if movement_request
            else [],
        },
        "npc_facts": relevant_npc_facts,
        "addressed_npc_context": {
            "id": addressed_npc_id,
            "facts": [list(fact) for fact in speaker_facts],
        },
        "inventory": list(state.player.inventory),
        "recent_events": [
            str(event.message_key).strip() for event in state.event_log.events[-5:] if str(event.message_key).strip()
        ],
    }
    system = (
        "You are Freeform Action Planner Agent. "
        "Return JSON only with keys dialog_proposal and action_proposal. "
        "dialog_proposal requires: speaker, text, tone. "
        "action_proposal requires: intent, targets, arguments, disclosed_knowledge, proposed_effects. "
        "Use only entities from provided context. "
        "For uncertain targets, use an empty targets list and a generic intent. "
        "Do not auto-target a visible NPC for a world interaction unless the player clearly addressed "
        "or questioned that NPC. "
        "If the player clearly addresses or questions a visible NPC, dialog_proposal.speaker must be that NPC and "
        "must use the exact canonical id in addressed_npc_context.id, "
        "dialog_proposal.text must be the NPC's in-character reply, not the player's line and not narrator summary. "
        "When answering appearance or clothing questions, treat npc_facts.appearance as authoritative "
        "and do not invent conflicting wardrobe details. "
        "For an addressed NPC, use addressed_npc_context only for that NPC's private knowledge; "
        "do not infer global truth. "
        "dialog_proposal.text must answer the player's meaning in new in-world prose; never simply repeat "
        "or quote player_input. For a readable document, describe its fact-backed contents or the immediate "
        "in-world consequence of reviewing it. "
        "When an addressed NPC reveals a document fact not known to the player, set disclosed_knowledge to "
        "that fact key; otherwise use an empty string. "
        "Write grounded roleplay: characters act from supplied motivations, relationships, knowledge, "
        "pressure, and limits, with room for initiative, subtext, disagreement, and hesitation. "
        "Performance may shape voice, attention, body language, pacing, and expression, but cannot invent "
        "facts, hidden knowledge, events, or visible state changes."
    )
    return system, json.dumps(payload, ensure_ascii=True)


def _normalize_intent(intent: str) -> str:
    normalized = _normalize_target(intent)
    if normalized in {"examine", "inspect", "review", "read", "analyze"}:
        return "inspect"
    if normalized in {"ask", "question", "query"}:
        return "ask_about"
    return normalized


def _normalize_action_payload(action_payload: dict[str, Any]) -> dict[str, Any]:
    intent = _normalize_intent(str(action_payload.get("intent", "")))
    targets = [_normalize_target(str(target)) for target in action_payload.get("targets", [])]
    raw_arguments = action_payload.get("arguments", {})
    arguments = {str(k): str(v) for k, v in raw_arguments.items()} if isinstance(raw_arguments, dict) else {}
    proposed_effects = [str(effect) for effect in action_payload.get("proposed_effects", [])]
    if intent:
        arguments.setdefault("planner_intent_raw", intent)
    return {
        "intent": intent or "freeform",
        "targets": [target for target in targets if target],
        "arguments": arguments,
        "disclosed_knowledge": str(action_payload.get("disclosed_knowledge", "")).strip(),
        "proposed_effects": proposed_effects,
    }


def _has_invalid_targeted_dialogue_speaker(
    state: GameState,
    dialog_payload: dict[str, Any],
    action_payload: dict[str, Any],
) -> bool:
    targets = action_payload.get("targets", ())
    if not isinstance(targets, (list, tuple)) or not any(str(target).strip() for target in targets):
        return False
    speaker = _normalized_dialog_speaker_id(state, str(dialog_payload.get("speaker", "")), action_payload)
    if speaker in {"narrator", "player"}:
        return True
    primary_target = _normalized_dialog_speaker_id(
        state,
        str(next((target for target in targets if str(target).strip()), "")),
        action_payload,
    )
    return bool(primary_target and speaker != primary_target)


def _dialogue_contains_code_artifact(dialog_payload: dict[str, Any]) -> bool:
    text = str(dialog_payload.get("text", "")).strip()
    if not text:
        return False
    return _CODE_ARTIFACT_TOKEN_PATTERN.search(text) is not None


def _scope_normalized_proposals(
    state: GameState,
    raw_input: str,
    dialog_payload: dict[str, Any],
    action_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if _explicit_npc_address_requested(raw_input):
        return dialog_payload, action_payload

    visible_npcs = set(room_npcs(state, player_location(state)))
    targets = tuple(str(target) for target in action_payload.get("targets", ()))
    npc_targets = tuple(target for target in targets if target in visible_npcs)
    if not npc_targets:
        return dialog_payload, action_payload

    cleaned_targets = tuple(target for target in targets if target not in visible_npcs)
    arguments = dict(action_payload.get("arguments", {}))
    arguments["scope_normalized"] = "scene"

    intent = str(action_payload.get("intent", "")).strip().lower()
    if not cleaned_targets and intent in _ALLOWED_INTENTS:
        intent = "freeform"
    normalized_action = {
        "intent": intent or "freeform",
        "targets": cleaned_targets,
        "arguments": arguments,
        "proposed_effects": tuple(str(effect) for effect in action_payload.get("proposed_effects", ())),
    }

    normalized_dialog = dialog_payload
    speaker = _normalized_dialog_speaker_id(state, str(dialog_payload.get("speaker", "")), action_payload)
    if speaker in visible_npcs:
        normalized_dialog = {
            "speaker": "narrator",
            "text": "You act on the scene before anyone answers.",
            "tone": "in_world",
        }
    elif speaker == "player":
        normalized_dialog = _scene_scoped_dialog_override(state, raw_input, action_payload)
    return normalized_dialog, normalized_action


def _scene_scoped_dialog_override(
    state: GameState,
    raw_input: str,
    action_payload: dict[str, Any],
) -> dict[str, Any]:
    normalized_input = _normalize_target(raw_input).replace("_", " ")
    visible_items = room_items(state, player_location(state))
    vehicle_names = {
        _normalize_target(state.world.items[item_id].name).replace("_", " ")
        for item_id in visible_items
        if item_id in state.world.items and state.world.items[item_id].kind == "vehicle"
    }
    if vehicle_names and (
        any(name and name in normalized_input for name in vehicle_names)
        or any(token in normalized_input for token in ("vehicle", "car", "door"))
    ):
        return {
            "speaker": "narrator",
            "text": f"You reach for the {next(iter(vehicle_names))}'s door, testing what gives before you commit further.",
            "tone": "in_world",
        }

    text = " ".join(str(action_payload.get("intent", "")).split()).strip()
    if _LOW_SIGNAL_PLAYER_ECHO_PATTERN.search(raw_input) or not text or text == "freeform":
        return {
            "speaker": "narrator",
            "text": "You focus on the immediate action.",
            "tone": "in_world",
        }
    return {
        "speaker": "narrator",
        "text": "You act on the scene before anyone answers.",
        "tone": "in_world",
    }


class LlmFreeformProposalAdapter:
    def __init__(self, *_ignored: object, **_ignored_options: object) -> None:
        pass

    def propose(self, state: GameState, raw_input: str) -> tuple[dict[str, Any], dict[str, Any]]:
        system, user = _freeform_planner_prompt(state, raw_input)
        try:
            dialog_payload, action_payload = self._planned_payloads(state, raw_input, system, user)
            dialog_payload, action_payload = _scope_normalized_proposals(
                state, raw_input, dialog_payload, action_payload
            )
            action_payload = _normalized_movement_action_payload(state, raw_input, action_payload)
            arguments = dict(action_payload["arguments"])
            arguments["planner_source"] = "llm"
            action_payload["arguments"] = arguments
            return dialog_payload, action_payload
        except Exception as exc:
            raise OrdinaryTurnRecoveryExhausted(exc) from exc

    def _planned_payloads(
        self,
        state: GameState,
        raw_input: str,
        system: str,
        user: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            return self._validated_planner_payloads(state, raw_input, system, user)
        except Exception as exc:
            retry_system = (
                system
                + " Your previous planner reply failed local validation "
                + f"({str(exc)[:120]}). Retry now with both proposal objects complete and "
                + "return JSON only, with no prose before or after the object."
            )
            return self._validated_planner_payloads(state, raw_input, retry_system, user)

    def _validated_planner_payloads(
        self,
        state: GameState,
        raw_input: str,
        system: str,
        user: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        dialog_payload, action_payload = self._parse_planner_response(state, raw_input, system, user)
        if _explicit_npc_address_requested(raw_input) and _has_invalid_targeted_dialogue_speaker(
            state, dialog_payload, action_payload
        ):
            raise ValueError("planner_invalid_targeted_dialogue_speaker")
        required_disclosure = _required_document_disclosure(state, raw_input, action_payload)
        if required_disclosure and action_payload.get("disclosed_knowledge") != required_disclosure:
            raise ValueError("planner_missing_required_document_disclosure")
        if _dialogue_conflicts_with_held_item_custody(state, str(dialog_payload.get("text", ""))):
            raise ValueError("planner_dialogue_custody_conflict")
        if _dialogue_contains_code_artifact(dialog_payload):
            raise ValueError("planner_dialogue_code_artifact")
        if is_player_statement_echo(raw_input, str(dialog_payload.get("text", ""))):
            raise ValueError("planner_dialogue_player_echo")
        return dialog_payload, action_payload

    def _parse_planner_response(
        self,
        state: GameState,
        raw_input: str,
        system: str,
        user: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = _story_agent_json_from_text(_story_agent_chat_complete("cloudflare", system, user))
        if payload is None:
            raise ValueError("planner_non_json")
        dialog_payload = parse_dialog_proposal(dict(payload.get("dialog_proposal", {})))
        raw_action_payload = _normalize_action_payload(dict(payload.get("action_proposal", {})))
        action_payload = parse_action_proposal(
            _normalized_movement_action_payload(state, raw_input, raw_action_payload)
        )
        return dialog_payload, parse_action_proposal(
            bind_direct_npc_conversation_target(state, raw_input, action_payload)
        )


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
            if room.item_ids:
                first_item = room.item_ids[0].replace("_", " ")
                room_label = room.id.replace("_", " ")
                return f"You ask {speaker} what stands out at {room_label}, with the {first_item} already drawing attention."
            exits = [
                next(
                    (
                        str(fact[3])
                        for fact in state.world_facts.query("path_label", state.player.location, route_id, None)
                    ),
                    route_id.replace("_", " "),
                )
                for route_id in sorted(room.exits)
            ]
            if exits:
                return f"You ask {speaker} what {room.name} suggests before either of you pushes {exits[0]}."
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
    readable_item = _readable_item_for_input(state, raw_input)
    if readable_item and re.search(r"\b(read|review|examine|inspect)\b", lowered):
        action = {
            "intent": "read",
            "targets": [readable_item],
            "arguments": {"source_command": "read"},
            "proposed_effects": [f"read:{readable_item}"],
        }
        return parse_action_proposal(action), dialog_proposal
    return action_proposal, dialog_proposal


def _envelope_for_action(state: GameState, action_proposal: dict[str, Any], raw_input: str = "") -> dict[str, Any]:
    targets = tuple(action_proposal["targets"])
    intent = str(action_proposal["intent"]).strip().lower()
    if not intent:
        intent = "freeform"

    if intent in _ALLOWED_INTENTS and not targets:
        return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_NO_TARGET"]}

    if intent == "read" and targets:
        item_id = str(targets[0])
        nearby_holder = _nearby_holder_for_item(state, item_id)
        visible_items = room_items(state, player_location(state))
        if not state.world_facts.holds("item_affordance", item_id, "read"):
            return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_UNREADABLE_ITEM"]}
        if item_id not in state.player.inventory and item_id not in visible_items and not nearby_holder:
            return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_UNAVAILABLE_ITEM"]}
        discovery = next((fact[2] for fact in state.world_facts.query("document_discovery", item_id, None)), item_id)
        assert_ops = [
            {"fact": ["flag", "player", f"reviewed_{item_id}"]},
            {"fact": ["flag", "player", f"freeform_intent_read_{item_id}"]},
            {"fact": ["discovered_clue", discovery]},
        ]
        assert_ops.extend(
            {"fact": ["discovered_lead", item_id, fact[2]]}
            for fact in state.world_facts.query("document_lead", item_id, None)
        )
        assert_ops.extend(
            {"fact": ["knows", "player", fact[2]]}
            for fact in state.world_facts.query("document_knowledge", item_id, None)
        )
        assert_ops.extend(
            {"fact": ["player_context", fact[2], fact[3]]}
            for fact in state.world_facts.query("document_context", item_id, None)
        )
        case_values = {fact[1]: fact[2] for fact in state.world_facts.query("case_fact", None, None)}
        assert_ops.extend(
            {
                "fact": [
                    "player_context",
                    f"{item_id}_{str(fact[2]).removesuffix('_name').split('_')[-1]}",
                    str(fact[3]).replace("{value}", case_values.get(fact[2], "")),
                ]
            }
            for fact in state.world_facts.query("document_context_template", item_id, None)
            if case_values.get(fact[2], "")
        )
        if nearby_holder:
            assert_ops.append({"fact": ["reviewed_with_holder", nearby_holder, item_id]})
        return {
            "assert": assert_ops,
            "retract": [
                {"fact": ["player_context", fact[2], fact[3]]}
                for fact in state.world_facts.query("document_retract_context", item_id, None)
            ],
            "numeric_delta": [],
            "reasons": [f"freeform:read_{item_id}"],
        }

    disclosed_knowledge = str(action_proposal.get("disclosed_knowledge", "")).strip()
    if disclosed_knowledge and targets:
        speaker_id = str(targets[0])
        document_id = _readable_item_for_input(state, raw_input) if raw_input else ""
        permitted = bool(document_id) and state.world_facts.holds(
            "document_disclosure", document_id, speaker_id, disclosed_knowledge
        )
        if (
            permitted
            and speaker_id in room_npcs(state, player_location(state))
            and state.world_facts.holds("knows", speaker_id, disclosed_knowledge)
            and not state.world_facts.holds("knows", "player", disclosed_knowledge)
        ):
            return {
                "assert": [{"fact": ["knows", "player", disclosed_knowledge]}],
                "retract": [],
                "numeric_delta": [],
                "reasons": [f"freeform:disclose_{disclosed_knowledge}"],
            }
        return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_INVALID_DISCLOSURE"]}

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
    if "POLICY_UNREADABLE_ITEM" in reasons or "POLICY_UNAVAILABLE_ITEM" in reasons:
        return 0.0, 0.0

    progress = 0.01
    tension = 0.01
    if any(reason.startswith("freeform:read_") for reason in reasons):
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


def _semantic_actions_for_freeform(
    state: GameState,
    action_proposal: dict[str, Any],
    envelope: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    del envelope
    intent = str(action_proposal.get("intent", "")).strip().lower()
    targets = tuple(str(target) for target in action_proposal.get("targets", ()) if str(target).strip())
    room_id = state.player.location

    if intent == "move" and targets:
        target = targets[0]
        exits = state.world.rooms[room_id].exits
        destination = exits.get(target, target if target in exits.values() else "")
        if destination:
            return (
                {
                    "action_id": f"freeform-move-{state.turn_index + 1}",
                    "action_type": "move_to",
                    "actor_id": "player",
                    "target_id": "",
                    "item_id": "",
                    "location_id": destination,
                },
            )

    if intent in {"take", "get", "grab"} and targets:
        item_id = targets[0]
        if item_id in state.world.rooms[room_id].item_ids:
            return (
                {
                    "action_id": f"freeform-take-{state.turn_index + 1}",
                    "action_type": "take_item",
                    "actor_id": "player",
                    "target_id": "",
                    "item_id": item_id,
                    "location_id": room_id,
                },
            )

    return ()


def _envelope_to_fact_ops(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    fact_ops: list[dict[str, Any]] = []
    for mutation in envelope["assert"]:
        fact_ops.append({"op": "assert", "fact": tuple(mutation["fact"])})
    for mutation in envelope["retract"]:
        fact_ops.append({"op": "retract", "fact": tuple(mutation["fact"])})
    for metric in envelope["numeric_delta"]:
        fact_ops.append({"op": "numeric_delta", "key": metric["key"], "delta": metric["delta"]})
    return fact_ops


def _format_character_reply_line(
    state: GameState,
    dialog_proposal: dict[str, Any],
    action_proposal: dict[str, Any] | None = None,
) -> str:
    speaker_id = str(dialog_proposal.get("speaker", "")).strip()
    text = " ".join(str(dialog_proposal.get("text", "")).split()).strip()
    if not text:
        return ""
    normalized_speaker = _normalized_dialog_speaker_id(state, speaker_id, action_proposal)
    if normalized_speaker in {"", "narrator"}:
        return text
    if normalized_speaker == "player":
        return text
    if _normalize_target(speaker_id) in {"ai_assistant", "assistant"} and action_proposal is not None:
        targets = action_proposal.get("targets", ())
        if isinstance(targets, (list, tuple)):
            for target in targets:
                candidate = _normalize_target(str(target))
                if candidate in state.world.npcs:
                    normalized_speaker = candidate
                    break

    npc = state.world.npcs.get(normalized_speaker)
    speaker_name = npc_reference_name(state, npc) if npc is not None else normalized_speaker.replace("_", " ").title()
    double_quoted = re.search(r'"([^"]+)"', text)
    if '"' in text:
        spoken = double_quoted.group(1).strip() if double_quoted is not None else text.strip(" \"'")
    elif " says, '" in text and text.endswith("'"):
        spoken = text.split(" says, '", 1)[1][:-1].strip()
    elif text.startswith("'") and text.endswith("'") and len(text) >= 2 and " " in text[1:-1]:
        spoken = text[1:-1].strip()
    elif double_quoted is not None:
        spoken = double_quoted.group(1).strip()
    else:
        spoken = text.strip()
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
    for npc_id in room_npcs(state, player_location(state)):
        npc = state.world.npcs.get(npc_id)
        if npc is None:
            continue
        npc_name = _normalize_target(npc.name)
        if npc_name and normalized.startswith(f"{npc_name}_"):
            return npc_id
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
    dialog_proposal, action_proposal = _scope_normalized_proposals(state, raw_input, dialog_proposal, action_proposal)
    dialog_proposal = parse_dialog_proposal(dialog_proposal)
    action_proposal = parse_action_proposal(action_proposal)
    action_proposal, dialog_proposal = _apply_raw_command_overrides(
        state,
        raw_input,
        action_proposal,
        dialog_proposal,
    )
    envelope = parse_state_update_envelope(_envelope_for_action(state, action_proposal, raw_input))
    if "POLICY_TARGET_NOT_PRESENT" in envelope["reasons"]:
        dialog_proposal = parse_dialog_proposal(
            {
                "speaker": "narrator",
                "text": "No one here answers that. Try speaking to someone in the room.",
                "tone": "boundary",
            }
        )
    envelope = parse_state_update_envelope(_envelope_with_story_deltas(action_proposal, envelope))

    targeted_npc_conversation = bool(action_proposal["targets"]) and _explicit_npc_address_requested(raw_input)
    turn_proposal = parse_turn_proposal(
        {
            "turn_id": f"freeform-{state.turn_index + 1}",
            "mode": "conversation" if targeted_npc_conversation else "scene",
            "player_intent": {
                "summary": str(action_proposal["intent"]),
                "addressed_npc_id": str(action_proposal["targets"][0]) if targeted_npc_conversation else "",
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
                "speaker_id": _normalized_dialog_speaker_id(
                    state, str(dialog_proposal.get("speaker", "")), action_proposal
                ),
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
            committed_fact_ops.extend(
                {"op": "numeric_delta", "key": entry["key"], "delta": entry["delta"]} for entry in numeric_delta
            )

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


DEFAULT_FREEFORM_ADAPTER = RuleBasedFreeformProposalAdapter()
