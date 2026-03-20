from __future__ import annotations

from random import Random

from storygame.engine.events import apply_event_template, select_event
from storygame.engine.facts import (
    active_story_goal,
    hidden_story_threads,
    planned_story_events,
    reveal_schedule,
    set_active_story_goal,
    story_goals,
)
from storygame.engine.incidents import realize_beat_incident
from storygame.engine.parser import Action
from storygame.engine.rules import apply_action
from storygame.engine.state import Event, GameState
from storygame.plot.beat_manager import select_beat
from storygame.plot.tension import apply_tension_events


def _goal_bundle(state: GameState) -> dict[str, object]:
    fact_goals = story_goals(state)
    if fact_goals["setup"] or fact_goals["primary"] or fact_goals["secondary"]:
        return fact_goals
    bundle = dict(state.world_package.get("llm_story_bundle", {}))
    if bundle:
        return {
            "setup": str(bundle.get("actionable_objective", "")).strip(),
            "primary": str(bundle.get("primary_goal", "")).strip(),
            "secondary": tuple(
                str(goal).strip() for goal in bundle.get("secondary_goals", ()) if str(goal).strip()
            ),
        }
    return dict(state.world_package.get("goals", {}))


def _story_plan_bundle(state: GameState) -> dict[str, object]:
    planned_events = planned_story_events(state)
    hidden_threads = hidden_story_threads(state)
    scheduled_reveals = reveal_schedule(state)
    if planned_events or hidden_threads or scheduled_reveals:
        return {
            "timed_events": planned_events,
            "hidden_threads": hidden_threads,
            "reveal_schedule": scheduled_reveals,
        }
    bundle = dict(state.world_package.get("llm_story_bundle", {}))
    if bundle:
        return {
            "timed_events": tuple(bundle.get("timed_events", ())),
            "hidden_threads": tuple(
                str(thread).strip() for thread in bundle.get("hidden_threads", ()) if str(thread).strip()
            ),
            "reveal_schedule": tuple(bundle.get("reveal_schedule", ())),
        }
    return dict(state.world_package.get("story_plan", {}))


def _refresh_active_goal(state: GameState) -> None:
    goals = _goal_bundle(state)
    setup_goal = str(goals.get("setup", "")).strip()
    primary_goal = str(goals.get("primary", "")).strip()
    secondary_goals = tuple(str(goal).strip() for goal in goals.get("secondary", ()) if str(goal).strip())

    if setup_goal and state.turn_index <= 3 and state.progress < 0.2:
        state.active_goal = setup_goal
        set_active_story_goal(state, setup_goal)
        return

    if secondary_goals and state.progress >= 0.75:
        state.active_goal = secondary_goals[0]
        set_active_story_goal(state, state.active_goal)
        return

    if primary_goal:
        state.active_goal = primary_goal
        set_active_story_goal(state, state.active_goal)


def _story_reveal_events(state: GameState) -> list[Event]:
    story_plan = _story_plan_bundle(state)
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


def _timed_story_events(state: GameState) -> list[Event]:
    story_plan = _story_plan_bundle(state)
    timed_events = tuple(entry for entry in story_plan.get("timed_events", ()) if isinstance(entry, dict))
    emitted: list[Event] = []
    for entry in timed_events:
        event_id = str(entry.get("event_id", "")).strip()
        summary = str(entry.get("summary", "")).strip()
        min_turn = int(entry.get("min_turn", 9999))
        if not event_id or not summary or state.turn_index < min_turn:
            continue
        flag = f"timed_story_event_{event_id}"
        if state.player.flags.get(flag, False):
            continue
        state.player.flags[flag] = True
        emitted.append(
            Event(
                type="timed_story_event",
                message_key=summary,
                entities=tuple(str(name).strip() for name in entry.get("participants", ()) if str(name).strip()),
                tags=("story", "timed_event"),
                turn_index=state.turn_index,
                delta_tension=0.03,
            )
        )
    return emitted


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

    timed_events = _timed_story_events(next_state)
    if timed_events:
        next_state.append_events(timed_events)
        next_state = apply_events_to_state(next_state, timed_events)

    all_events = action_events + narrative_events + reveal_events + timed_events
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
