from __future__ import annotations

from random import Random
from typing import Any

from storygame.engine.events import apply_event_template, select_event
from storygame.engine.facts import (
    dramatic_metric,
    set_active_story_goal,
    set_dramatic_metric,
    story_goals,
)
from storygame.engine.incidents import realize_beat_incident
from storygame.engine.parser import Action
from storygame.engine.rules import apply_action
from storygame.engine.scene_state import refresh_scene_state
from storygame.engine.state import Event, GameState
from storygame.plot.beat_manager import select_beat
from storygame.plot.beat_policy import BeatPolicy
from storygame.plot.dramatic_policy import turn_focus_from_action
from storygame.plot.tension import apply_tension_events


def _goal_bundle(state: GameState) -> dict[str, Any]:
    fact_goals = story_goals(state)
    if fact_goals["setup"] or fact_goals["primary"] or fact_goals["secondary"]:
        return fact_goals
    return dict(state.world_package.get("goals", {}))


def _refresh_active_goal(state: GameState) -> None:
    goals = _goal_bundle(state)
    setup_goal = str(goals.get("setup", "")).strip()
    primary_goal = str(goals.get("primary", "")).strip()
    secondary_goals = tuple(str(goal).strip() for goal in goals.get("secondary", ()) if str(goal).strip())

    if setup_goal and state.turn_index <= 3 and state.progress < 0.2:
        set_active_story_goal(state, setup_goal)
        return

    if secondary_goals and state.progress >= 0.75:
        set_active_story_goal(state, secondary_goals[0])
        return

    if primary_goal:
        set_active_story_goal(state, primary_goal)


def _story_reveal_events(state: GameState) -> list[Event]:
    return [event for event in BeatPolicy().progression_events(state) if event.type == "story_reveal"]


def _timed_story_events(state: GameState) -> list[Event]:
    return [event for event in BeatPolicy().progression_events(state) if event.type == "timed_story_event"]


def apply_events_to_state(state: GameState, events: list[Event]) -> GameState:
    if not events:
        _refresh_active_goal(state)
        refresh_scene_state(state)
        return state
    for event in events:
        state.progress = max(0.0, min(1.0, dramatic_metric(state, "progress", state.progress) + event.delta_progress))
        state.tension = max(0.0, min(1.0, dramatic_metric(state, "tension", state.tension) + event.delta_tension))
    set_dramatic_metric(state, "progress", state.progress)
    set_dramatic_metric(state, "tension", state.tension)
    state = apply_tension_events(state, events)
    _refresh_active_goal(state)
    refresh_scene_state(state)
    return state


def run_post_commit_story(
    state: GameState,
    action_events: list[Event],
    rng: Random,
) -> tuple[GameState, list[Event], str, str]:
    next_state = state.clone()

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

    progression_events = BeatPolicy().progression_events(next_state)
    reveal_events = [event for event in progression_events if event.type == "story_reveal"]
    if reveal_events:
        next_state.append_events(reveal_events)
        next_state = apply_events_to_state(next_state, reveal_events)

    timed_events = [event for event in progression_events if event.type == "timed_story_event"]
    if timed_events:
        next_state.append_events(timed_events)
        next_state = apply_events_to_state(next_state, timed_events)

    all_events = narrative_events + reveal_events + timed_events
    return next_state, all_events, beat.type, template_key


def advance_turn(
    state: GameState,
    action: Action,
    rng: Random,
) -> tuple[GameState, list[Event], str, str]:
    world_state, action_events = apply_action(state, action, rng)

    next_state = world_state.clone()
    next_state.append_events(action_events)
    next_state = apply_events_to_state(next_state, action_events)
    refresh_scene_state(next_state, turn_focus_from_action(next_state, action))

    next_state, followup_events, beat_type, template_key = run_post_commit_story(next_state, action_events, rng)
    all_events = action_events + followup_events
    return next_state, all_events, beat_type, template_key


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
