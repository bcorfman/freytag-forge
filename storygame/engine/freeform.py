from __future__ import annotations

import re
from typing import Any, Protocol, TypedDict

from storygame.engine.facts import apply_fact_ops, player_location, room_npcs
from storygame.engine.interfaces import parse_action_proposal, parse_dialog_proposal, parse_state_update_envelope
from storygame.engine.state import Event, GameState

_TOPIC_TOKEN = re.compile(r"[^a-z0-9]+")
_ASK_TARGET_PATTERN = re.compile(r"\bask\s+([a-z0-9_]+)\b")
_ALLOWED_TOPIC_FLAGS = {
    "signal",
    "rumor",
    "rumors",
    "ledger",
    "sanctuary",
    "bell",
}
_ALLOWED_INTENTS = {"ask_about", "greet", "apologize", "threaten"}
_PER_TURN_DELTA_BOUND = 0.15
_TOPIC_STOPWORDS = {"the", "a", "an", "about", "of", "to"}


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
        visible_npcs = room_npcs(state, player_location(state))

        ask_target_match = _ASK_TARGET_PATTERN.search(text)
        target = ask_target_match.group(1) if ask_target_match is not None else ""
        if not target:
            for npc_id in visible_npcs:
                if npc_id in text:
                    target = npc_id
                    break
        if not target and visible_npcs:
            target = visible_npcs[0]

        intent = "ask_about"
        topic = "rumors"
        if text.startswith(("hi", "hello", "greet")):
            intent = "greet"
            topic = ""
        elif "sorry" in text or "apolog" in text:
            intent = "apologize"
            topic = ""
        elif "threat" in text or "warn" in text:
            intent = "threaten"
            topic = ""
        elif "about" in text:
            topic = text.split("about", 1)[1].strip() or "rumors"

        action_payload = {
            "intent": intent,
            "targets": [target] if target else [],
            "arguments": {"topic": topic} if topic else {},
            "proposed_effects": [f"{intent}:{target or 'none'}"],
        }
        speaker = target or "narrator"
        response = _dialog_line(intent=intent, target=target, topic=topic)
        dialog_payload = {"speaker": speaker, "text": response, "tone": "in_world"}
        return dialog_payload, action_payload


def _dialog_line(intent: str, target: str, topic: str) -> str:
    if not target:
        return "Only the tide answers; no one here responds to that."
    if intent == "greet":
        return f"{target.title()} nods once. 'Speak your purpose and keep your footing.'"
    if intent == "apologize":
        return f"{target.title()} exhales. 'Fine. Keep it clean from here on.'"
    if intent == "threaten":
        return f"{target.title()} narrows their eyes. 'Threats travel farther than you think.'"
    if topic:
        return f"{target.title()} lowers their voice. 'About {topic}: follow the signal and the records.'"
    return f"{target.title()} studies you, waiting for a clearer question."


def _topic_flag_fragment(raw_topic: str) -> str:
    normalized = _TOPIC_TOKEN.sub("_", raw_topic.lower()).strip("_")
    if not normalized:
        return "rumors"
    for token in normalized.split("_"):
        if token and token not in _TOPIC_STOPWORDS:
            return token
    return "rumors"


def _envelope_for_action(state: GameState, action_proposal: dict[str, Any]) -> dict[str, Any]:
    targets = tuple(action_proposal["targets"])
    if not targets:
        return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_NO_TARGET"]}

    target = str(targets[0])
    visible_npcs = room_npcs(state, player_location(state))
    if target not in visible_npcs:
        return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_TARGET_NOT_PRESENT"]}

    intent = str(action_proposal["intent"])
    if intent not in _ALLOWED_INTENTS:
        return {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["POLICY_INTENT_NOT_ALLOWED"]}

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


def _envelope_to_fact_ops(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    fact_ops: list[dict[str, Any]] = []
    for mutation in envelope["assert"]:
        fact_ops.append({"op": "assert", "fact": tuple(mutation["fact"])})
    for mutation in envelope["retract"]:
        fact_ops.append({"op": "retract", "fact": tuple(mutation["fact"])})
    for metric in envelope["numeric_delta"]:
        fact_ops.append({"op": "numeric_delta", "key": metric["key"], "delta": metric["delta"]})
    return fact_ops


def resolve_freeform_roleplay(
    state: GameState,
    raw_input: str,
    adapter: FreeformProposalAdapter,
) -> FreeformResolution:
    next_state = state.clone()
    next_state.turn_index += 1

    dialog_payload, action_payload = adapter.propose(next_state, raw_input)
    dialog_proposal = parse_dialog_proposal(dialog_payload)
    action_proposal = parse_action_proposal(action_payload)
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

    event = Event(
        type="freeform_roleplay",
        message_key=dialog_proposal["text"],
        entities=tuple(action_proposal["targets"]),
        tags=("dialog", "freeform"),
        turn_index=next_state.turn_index,
        metadata={
            "action_proposal": action_proposal,
            "dialog_proposal": dialog_proposal,
            "state_update_envelope": envelope,
            "fact_ops": fact_ops,
        },
    )
    next_state.append_event(event)
    return {
        "state": next_state,
        "event": event,
        "action_proposal": action_proposal,
        "dialog_proposal": dialog_proposal,
        "state_update_envelope": envelope,
    }


DEFAULT_FREEFORM_ADAPTER = RuleBasedFreeformProposalAdapter()
