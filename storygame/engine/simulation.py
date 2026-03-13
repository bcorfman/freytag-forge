from __future__ import annotations

from random import Random

from storygame.engine.events import apply_event_template, select_event
from storygame.engine.incidents import realize_beat_incident
from storygame.engine.parser import Action
from storygame.engine.rules import apply_action
from storygame.engine.state import Event, GameState
from storygame.plot.beat_manager import select_beat
from storygame.plot.tension import apply_tension_events


def _refresh_active_goal(state: GameState) -> None:
    goals = state.world_package.get("goals", {})
    setup_goal = str(goals.get("setup", "")).strip()
    primary_goal = str(goals.get("primary", "")).strip()
    secondary_goals = tuple(str(goal).strip() for goal in goals.get("secondary", ()) if str(goal).strip())

    if setup_goal and state.turn_index <= 3 and state.progress < 0.2:
        state.active_goal = setup_goal
        return

    if secondary_goals and state.progress >= 0.75:
        state.active_goal = secondary_goals[0]
        return

    if primary_goal:
        state.active_goal = primary_goal


def _story_reveal_events(state: GameState) -> list[Event]:
    package = state.world_package
    story_plan = package.get("story_plan", {})
    hidden_threads = tuple(
        str(thread).strip() for thread in story_plan.get("hidden_threads", ()) if str(thread).strip()
    )
    schedule = tuple(story_plan.get("reveal_schedule", ()))
    if not hidden_threads or not schedule:
        return []

    reveal_events: list[Event] = []
    for entry in schedule:
        if not isinstance(entry, dict):
            continue
        thread_index = int(entry.get("thread_index", -1))
        min_progress = float(entry.get("min_progress", 1.0))
        if thread_index < 0 or thread_index >= len(hidden_threads):
            continue
        if state.progress < min_progress:
            continue
        flag = f"story_reveal_{thread_index}"
        if state.player.flags.get(flag, False):
            continue

        reveal_text = hidden_threads[thread_index]
        state.player.flags[flag] = True
        reveal_events.append(
            Event(
                type="story_reveal",
                message_key=f"New lead: {reveal_text}",
                entities=(f"thread_{thread_index}",),
                tags=("story_reveal",),
                turn_index=state.turn_index,
                delta_tension=0.02,
            )
        )
    return reveal_events


def apply_events_to_state(state: GameState, events: list[Event]) -> GameState:
    if not events:
        _refresh_active_goal(state)
        return state
    for event in events:
        state.progress = max(0.0, min(1.0, state.progress + event.delta_progress))
        state.tension = state.tension + event.delta_tension
    state = apply_tension_events(state, events)
    _refresh_active_goal(state)
    return state


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

    next_state, incident_events = realize_beat_incident(next_state, beat, action_events, rng)
    if incident_events:
        narrative_events = incident_events
        template_key = f"incident:{incident_events[0].metadata['incident_id']}"
    else:
        template = select_event(beat, next_state, rng)
        template_key = template.key
        next_state, narrative_events = apply_event_template(next_state, template, rng)
    next_state = apply_events_to_state(next_state, narrative_events)

    reveal_events = _story_reveal_events(next_state)
    if reveal_events:
        next_state.append_events(reveal_events)
        next_state = apply_events_to_state(next_state, reveal_events)

    all_events = action_events + narrative_events + reveal_events
    return next_state, all_events, beat.type, template_key


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
