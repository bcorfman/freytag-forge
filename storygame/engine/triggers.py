from __future__ import annotations

from typing import Any

from storygame.engine.state import Event, GameState


def _fact_holds(state: GameState, fact: tuple[str, ...]) -> bool:
    predicate, *terms = fact
    return state.world_facts.holds(predicate, *terms)


def _last_trigger_turn(state: GameState, trigger_id: str) -> int | None:
    for event in reversed(state.event_log.events):
        if event.type != "trigger":
            continue
        if str(event.metadata.get("trigger_id", "")) == trigger_id:
            return event.turn_index
    return None


def _matches_action(trigger: dict[str, Any], event: Event) -> bool:
    if event.type != "semantic_action":
        return False
    metadata = event.metadata
    if trigger["action_types"] and str(metadata.get("action_type", "")) not in trigger["action_types"]:
        return False
    if trigger["actor_ids"] and str(metadata.get("actor_id", "")) not in trigger["actor_ids"]:
        return False
    if trigger["target_ids"] and str(metadata.get("target_id", "")) not in trigger["target_ids"]:
        return False
    if trigger["item_ids"] and str(metadata.get("item_id", "")) not in trigger["item_ids"]:
        return False
    if trigger["location_ids"] and str(metadata.get("location_id", "")) not in trigger["location_ids"]:
        return False
    return True


def _trigger_eligible(trigger: dict[str, Any], state: GameState, action_events: tuple[Event, ...]) -> bool:
    if not trigger["enabled"]:
        return False
    if trigger["once"] and state.world_facts.holds("trigger_fired", trigger["trigger_id"]):
        return False
    if trigger["min_turn"] > 0 and state.turn_index < trigger["min_turn"]:
        return False
    cooldown_turns = int(trigger["cooldown_turns"])
    if cooldown_turns > 0:
        last_turn = _last_trigger_turn(state, trigger["trigger_id"])
        if last_turn is not None and state.turn_index - last_turn < cooldown_turns:
            return False
    if any(not _fact_holds(state, fact) for fact in trigger["required_facts"]):
        return False
    if any(_fact_holds(state, fact) for fact in trigger["forbidden_facts"]):
        return False
    if trigger["kind"] == "turn":
        if trigger["location_ids"] and state.player.location not in trigger["location_ids"]:
            return False
        return True
    return any(_matches_action(trigger, event) for event in action_events)


def evaluate_triggers(
    state: GameState,
    trigger_specs: tuple[dict[str, Any], ...],
    action_events: tuple[Event, ...],
) -> list[Event]:
    events: list[Event] = []
    for trigger in trigger_specs:
        if not _trigger_eligible(trigger, state, action_events):
            continue
        fact_ops = [{"op": "assert", "fact": entry["fact"]} for entry in trigger["effects"]["assert"]]
        fact_ops.extend({"op": "retract", "fact": entry["fact"]} for entry in trigger["effects"]["retract"])
        if trigger["once"]:
            fact_ops.append({"op": "assert", "fact": ("trigger_fired", trigger["trigger_id"])})
        events.append(
            Event(
                type="trigger",
                message_key=str(trigger["effects"]["emit_message"]),
                entities=(trigger["trigger_id"],),
                tags=("trigger", trigger["kind"]),
                turn_index=state.turn_index,
                metadata={
                    "trigger_id": trigger["trigger_id"],
                    "numeric_delta": list(trigger["effects"]["numeric_delta"]),
                    "reasons": list(trigger["effects"]["reasons"]),
                    "fact_ops": fact_ops,
                },
            )
        )
    return events
