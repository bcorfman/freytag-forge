from __future__ import annotations

from typing import TYPE_CHECKING, Any

from storygame.engine.facts import apply_fact_ops
from storygame.engine.scene_state import refresh_scene_state
from storygame.engine.semantic_actions import commit_semantic_action
from storygame.engine.state import Event, GameState
from storygame.engine.triggers import evaluate_triggers
from storygame.plot.dramatic_policy import turn_focus_from_proposal

if TYPE_CHECKING:
    from storygame.llm.contracts import NpcDialogueProposal, NumericDelta, TurnProposal


def _apply_numeric_deltas(state: GameState, numeric_delta: tuple[NumericDelta, ...] | list[NumericDelta]) -> None:
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


def _format_npc_dialogue_line(state: GameState, npc_dialogue: NpcDialogueProposal) -> str:
    speaker_id = str(npc_dialogue["speaker_id"]).strip()
    text = " ".join(str(npc_dialogue["text"]).split()).strip()
    if not speaker_id or not text:
        return ""
    npc = state.world.npcs.get(speaker_id)
    speaker_name = npc.name if npc is not None else speaker_id.replace("_", " ").title()
    return f'{speaker_name} says: "{text}"'


def _dialogue_lines_from_proposal(state: GameState, proposal: TurnProposal) -> tuple[str, ...]:
    line = _format_npc_dialogue_line(state, proposal["npc_dialogue"])
    if not line:
        return ()
    return (line,)


def _proposal_intent_summary(proposal: TurnProposal) -> str:
    return str(proposal["player_intent"]["summary"]).strip()


def execute_turn_proposal(state: GameState, proposal: TurnProposal, rng) -> dict[str, Any]:  # noqa: ARG001
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
    explicit_ops = [{"op": "assert", "fact": entry["fact"]} for entry in state_delta["assert_ops"]]
    explicit_ops.extend({"op": "retract", "fact": entry["fact"]} for entry in state_delta["retract_ops"])
    if explicit_ops:
        apply_fact_ops(next_state, explicit_ops)
    _apply_numeric_deltas(next_state, list(state_delta["numeric_delta"]))

    trigger_specs = tuple(next_state.world_package.get("trigger_specs", ()))
    triggered_events = evaluate_triggers(next_state, trigger_specs, tuple(action_events))
    for event in triggered_events:
        apply_fact_ops(next_state, event.metadata.get("fact_ops", ()))
        _apply_numeric_deltas(next_state, event.metadata.get("numeric_delta", ()))
        events.append(event)
        next_state.append_event(event)

    refresh_scene_state(next_state, turn_focus_from_proposal(next_state, proposal))

    return {
        "state": next_state,
        "events": events,
        "accepted_narration": proposal["narration"],
        "dialogue_lines": _dialogue_lines_from_proposal(next_state, proposal),
        "intent_summary": _proposal_intent_summary(proposal),
    }
