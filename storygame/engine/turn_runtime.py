from __future__ import annotations

from typing import Any

from storygame.engine.facts import apply_fact_ops
from storygame.engine.semantic_actions import commit_semantic_action
from storygame.engine.state import Event, GameState
from storygame.engine.triggers import evaluate_triggers


def _apply_numeric_deltas(state: GameState, numeric_delta: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> None:
    for entry in numeric_delta:
        key = str(entry["key"]).strip()
        delta = float(entry["delta"])
        if key == "progress":
            state.progress = max(0.0, min(1.0, state.progress + delta))
            continue
        if key == "tension":
            state.tension = max(0.0, min(1.0, state.tension + delta))
            continue
        state.fact_metrics[key] = state.fact_metrics.get(key, 0.0) + delta


def execute_turn_proposal(state: GameState, proposal: dict[str, Any], rng) -> dict[str, Any]:  # noqa: ARG001
    next_state = state.clone()
    next_state.turn_index += 1

    events: list[Event] = []
    action_events: list[Event] = []

    for action in proposal["semantic_actions"]:
        event = commit_semantic_action(next_state, action)
        apply_fact_ops(next_state, event.metadata.get("fact_ops", ()))
        action_events.append(event)
        events.append(event)
        next_state.append_event(event)

    state_delta = proposal["state_delta"]
    explicit_ops = [{"op": "assert", "fact": entry["fact"]} for entry in state_delta["assert"]]
    explicit_ops.extend({"op": "retract", "fact": entry["fact"]} for entry in state_delta["retract"])
    if explicit_ops:
        apply_fact_ops(next_state, explicit_ops)
    _apply_numeric_deltas(next_state, state_delta["numeric_delta"])

    trigger_specs = tuple(next_state.world_package.get("trigger_specs", ()))
    triggered_events = evaluate_triggers(next_state, trigger_specs, tuple(action_events))
    for event in triggered_events:
        apply_fact_ops(next_state, event.metadata.get("fact_ops", ()))
        _apply_numeric_deltas(next_state, event.metadata.get("numeric_delta", ()))
        events.append(event)
        next_state.append_event(event)

    return {
        "state": next_state,
        "events": events,
        "accepted_narration": proposal["narration"],
        "dialogue_lines": proposal["dialogue_lines"],
    }
