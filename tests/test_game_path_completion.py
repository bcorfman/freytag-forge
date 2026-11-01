"""Timing-boundary coverage for every declared pacing event, storylet window and exit floor.

Each case builds a state inside the scene, `turns_since_entry` accepted turns after
entry, with the declared prerequisites present or absent, and asserts what the
engine does just before, at and just after the boundary. Expected values come from
the package declarations and the plan's contract, not from the engine's own
branches: events fire at or after `at_turn` only when their `when` holds;
optional storylets close after `latest_turn`, required ones never do; the first
storylet of a scene (and any storylet whose earlier siblings have all fired) may
open before `earliest_turn`; an exit waits for `min_turns`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.incidents import resolved_incident_outcome
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.obligations import required_storylet_ids

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
REQUIRED = required_storylet_ids(PACKAGE)
WINDOWS = {window.scene_id: window for window in PACKAGE.pacing.scenes}
STORYLETS = PACKAGE.storylet_routes.storylets


def _assert_true(state: RuntimeState, fact_id: str) -> None:
    state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))


def _in_scene(scene_id: str, since_entry: int) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state._assert_scene_entry_fact(scene_id)
    state.scene_entered_at_turn = 0
    state.turn_index = since_entry
    return state


def _engine(state: RuntimeState) -> RuntimeEngine:
    return RuntimeEngine(state, lambda _command: {"segments": []})


def _satisfy(state: RuntimeState, predicates) -> None:
    for predicate in predicates:
        state.facts.assert_fact(Fact(predicate=predicate.fact_id, subject="story", value=str(predicate.equals).lower()))


def _is_true(state: RuntimeState, fact_id: str) -> bool:
    matching = state.facts.matching(fact_id)
    return bool(matching) and str(matching[0].value).lower() == "true"


def _has_value(state: RuntimeState, fact_id: str, value: bool) -> bool:
    return any(
        fact.predicate == fact_id and str(fact.value).lower() == str(value).lower() for fact in state.facts.asserted
    )


EVENTS = [event for event in PACKAGE.pacing.events if event.transition_id is None]


@pytest.mark.parametrize("event", EVENTS, ids=lambda event: event.id)
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_pressure_event_fires_at_its_turn_when_its_conditions_hold(event, offset) -> None:
    state = _in_scene(event.scene_id, max(event.at_turn + offset, 0))
    _satisfy(state, event.when)

    _engine(state)._activate_pacing()

    should_fire = event.at_turn + offset >= event.at_turn
    assert (event.id in state.fired_event_ids) is should_fire
    for effect in event.effects:
        if should_fire:
            assert _has_value(state, effect.fact_id, effect.equals)
        else:
            assert _is_true(state, effect.fact_id) is not effect.equals


@pytest.mark.parametrize("event", [event for event in EVENTS if event.when], ids=lambda event: event.id)
def test_pressure_event_with_missing_conditions_waits_then_fires_once_they_arrive(event) -> None:
    state = _in_scene(event.scene_id, event.at_turn + 3)
    state.fired_event_ids.update(
        prior.id for prior in EVENTS if prior.scene_id == event.scene_id and prior.at_turn < event.at_turn
    )
    engine = _engine(state)

    engine._activate_pacing()
    unmet = [p for p in event.when if p.equals is True]
    if unmet:
        assert event.id not in state.fired_event_ids

    _satisfy(state, event.when)
    state.turn_index += 1
    engine._activate_pacing()

    assert event.id in state.fired_event_ids
    assert all(_has_value(state, effect.fact_id, effect.equals) for effect in event.effects)


@pytest.mark.parametrize("event", EVENTS, ids=lambda event: event.id)
def test_pressure_event_fires_only_once(event) -> None:
    state = _in_scene(event.scene_id, event.at_turn)
    _satisfy(state, event.when)
    engine = _engine(state)

    engine._activate_pacing()
    effect = event.effects[0]
    first = [
        fact
        for fact in state.facts.asserted
        if fact.predicate == effect.fact_id and str(fact.value).lower() == str(effect.equals).lower()
    ]
    state.turn_index += 2
    engine._activate_pacing()
    second = [
        fact
        for fact in state.facts.asserted
        if fact.predicate == effect.fact_id and str(fact.value).lower() == str(effect.equals).lower()
    ]

    assert len(first) == len(second) == 1


@pytest.mark.parametrize("storylet", STORYLETS, ids=lambda storylet: storylet.id)
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_storylet_closes_after_latest_turn_unless_required(storylet, offset) -> None:
    since_entry = storylet.latest_turn + offset
    state = _in_scene(storylet.scene_id, since_entry)
    _satisfy(state, storylet.activation_conditions)
    # Earned-forward: every earlier sibling has been played, so the clock cannot be the reason it is closed.
    for earlier in STORYLETS:
        if earlier.scene_id == storylet.scene_id and earlier.target_turn < storylet.target_turn:
            state.fired_event_ids.add(earlier.id)
    state.active_event_ids.add(storylet.id)

    _engine(state)._activate_pacing()

    expected_open = storylet.id in REQUIRED or offset <= 0
    assert (storylet.id in state.active_event_ids) is expected_open


@pytest.mark.parametrize(
    "storylet",
    [item for item in STORYLETS if item.earliest_turn > 0],
    ids=lambda storylet: storylet.id,
)
def test_storylet_with_earlier_siblings_unplayed_waits_for_its_earliest_turn(storylet) -> None:
    earlier_siblings = [
        item for item in STORYLETS if item.scene_id == storylet.scene_id and item.target_turn < storylet.target_turn
    ]
    before = _in_scene(storylet.scene_id, storylet.earliest_turn - 1)
    at = _in_scene(storylet.scene_id, storylet.earliest_turn)
    for state in (before, at):
        _satisfy(state, storylet.activation_conditions)
        _engine(state)._activate_pacing()

    if earlier_siblings:
        assert storylet.id not in before.active_event_ids
    assert storylet.id in at.active_event_ids


@pytest.mark.parametrize("storylet", STORYLETS, ids=lambda storylet: storylet.id)
def test_storylet_stays_closed_while_an_activation_condition_is_unmet(storylet) -> None:
    needs = [p for p in storylet.activation_conditions if p.equals is True]
    if not needs:
        pytest.skip("no positive activation condition to withhold")
    state = _in_scene(storylet.scene_id, storylet.target_turn)

    _engine(state)._activate_pacing()

    assert storylet.id not in state.active_event_ids


@pytest.mark.parametrize("transition", PACKAGE.pacing.transitions, ids=lambda transition: transition.id)
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_authored_exit_waits_for_the_scene_floor(transition, offset) -> None:
    window = WINDOWS[transition.source_scene_id]
    state = _in_scene(transition.source_scene_id, max(window.min_turns + offset, 0))
    _satisfy(state, transition.triggers)

    result = _engine(state)._apply_authored_transition()

    incident = next((item for item in PACKAGE.incidents if item.scene_id == transition.source_scene_id), None)
    incident_resolved = incident is not None and resolved_incident_outcome(incident, state.facts) is not None
    expected_exit = offset >= 0 or incident_resolved
    assert (result is not None) is expected_exit
    assert (state.current_scene_id == transition.target_scene_id) is expected_exit


@pytest.mark.parametrize("transition", PACKAGE.pacing.transitions, ids=lambda transition: transition.id)
def test_authored_exit_never_fires_without_its_triggers(transition) -> None:
    window = WINDOWS[transition.source_scene_id]
    state = _in_scene(transition.source_scene_id, window.handoff_after_turns + 5)

    result = _engine(state)._apply_authored_transition()

    assert result is None
    assert state.current_scene_id == transition.source_scene_id
