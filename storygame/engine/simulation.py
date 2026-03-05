from __future__ import annotations

from random import Random

from storygame.engine.events import apply_event_template, select_event
from storygame.engine.parser import Action
from storygame.engine.rules import apply_action
from storygame.engine.state import Event, GameState
from storygame.plot.beat_manager import select_beat
from storygame.plot.tension import apply_tension_events


def apply_events_to_state(state: GameState, events: list[Event]) -> GameState:
    if not events:
        return state
    for event in events:
        state.progress = max(0.0, min(1.0, state.progress + event.delta_progress))
        state.tension = state.tension + event.delta_tension
    return apply_tension_events(state, events)


def advance_turn(
    state: GameState,
    action: Action,
    rng: Random,
) -> tuple[GameState, list[Event], str, str]:
    world_state, action_events = apply_action(state, action, rng)

    next_state = world_state.clone()
    next_state.append_events(action_events)
    next_state = apply_events_to_state(next_state, action_events)

    beat = select_beat(next_state, rng)
    next_state.append_beat(beat.type)

    template = select_event(beat, next_state, rng)
    next_state, narrative_events = apply_event_template(next_state, template, rng)
    next_state = apply_events_to_state(next_state, narrative_events)

    all_events = action_events + narrative_events
    return next_state, all_events, beat.type, template.key


def run_command_sequence(
    state: GameState,
    commands: list[str],
    rng: Random,
) -> GameState:
    current = state
    for command in commands:
        from storygame.engine.parser import parse_command

        action = parse_command(command)
        current, _events, _beat, _template = advance_turn(current, action, rng)
    return current
