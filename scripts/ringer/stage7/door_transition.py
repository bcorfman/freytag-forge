"""Full 2B continuation for the Stage 7 transition screen."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from door_continuation import score_command
from door_probe import _ask_player
from door_transport import SpendBudget, counted_provider

from bench.core import load_variation, package_and_state, provider_for
from storygame.runtime.engine import RuntimeEngine


def run_continuation(
    variation_path: Path,
    first_command: str,
    screen: str,
    budget: SpendBudget,
    max_commands: int = 20,
    ask_player: Callable[[str, SpendBudget], str] = _ask_player,
) -> dict[str, Any]:
    """Run a fresh 2B state until its scene exits or the command cap is met."""

    variation = load_variation(variation_path)
    package, state = package_and_state(variation, "2B")
    provider = provider_for(state, variation)
    previous = getattr(provider, "semantic_ask", None)
    provider.semantic_ask = None
    engine = RuntimeEngine(state, provider)
    commands: list[str] = []
    responses: list[str] = []
    clarification_turns: list[int] = []
    committed_reveals_by_turn: list[list[str]] = []
    segments_dropped_by_turn: list[int] = []
    turn_statuses: list[str] = []
    ended_by = "none"
    transition_turn: int | None = None
    transcript = screen
    try:
        with counted_provider(provider, budget):
            command = first_command
            committed = frozenset()
            while len(commands) < max_commands:
                previous_turn = turn_statuses[-1] if turn_statuses else None
                previous_command = commands[-1] if commands else None
                turn = score_command(
                    engine,
                    state,
                    command,
                    clarifies=previous_command if previous_turn == "clarification" else None,
                    clarification_round=1 if previous_turn == "clarification" else 0,
                    already_committed=committed,
                )
                commands.append(command)
                segments_dropped_by_turn.append(int(state.last_turn_delivery.segments_dropped))
                responses.append(turn.get("response"))
                status = turn.get("status")
                turn_statuses.append(status)
                committed_ids = list(turn.get("committed_reveals", []))
                committed_reveals_by_turn.append(committed_ids)
                committed = frozenset((*committed, *committed_ids))
                transcript += f"\n\n> {command}\n{turn.get('response', '')}"
                if status == "clarification":
                    clarification_turns.append(len(commands))
                else:
                    cause = getattr(getattr(engine, "last_attempt", None), "transition_cause", "none")
                    if state.current_scene_id != "2B":
                        ended_by = cause
                        transition_turn = len(commands)
                        break
                    if state.story_complete:
                        break
                if len(commands) >= max_commands:
                    break
                command = ask_player(transcript, budget)
        return {
            "final_scene": state.current_scene_id,
            "ended_by": ended_by,
            "transition_turn": transition_turn,
            "commands": commands,
            "responses": responses,
            "clarification_turns": clarification_turns,
            "committed_reveals_by_turn": committed_reveals_by_turn,
            "segments_dropped_by_turn": segments_dropped_by_turn,
            "panel_named": any("panel" in command.lower() for command in commands),
            "turn_statuses": turn_statuses,
            "request_count": getattr(provider, "request_count", 0),
            "recovery_count": getattr(provider, "recovery_count", 0),
        }
    finally:
        provider.semantic_ask = previous
