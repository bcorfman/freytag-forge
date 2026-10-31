"""Cheap drift checks for the shared-prefix journey implementation."""

from __future__ import annotations

import pytest

from storygame.personas import PERSONAS, _resolution_complete, _ScriptedProvider, _select_thorough, _turn_cap
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from tests.journey_prefix import PLAYED, _blocked_for
from tests.test_game_path_journeys import Journey, play


def full_walk(preferred: tuple[str, ...]) -> Journey:
    blocked = _blocked_for(preferred)
    state = RuntimeState.bootstrap(PLAYED)
    provider = _ScriptedProvider(PLAYED, state)
    engine = RuntimeEngine(state, provider)
    journey = Journey(state=state, scenes=[state.current_scene_id])
    for _ in range(_turn_cap(PLAYED)):
        if _resolution_complete(state):
            break
        engine._activate_pacing()
        offered = tuple(
            candidate
            for candidate in engine.projector.project(state, "player", "").candidates
            if candidate.id not in blocked
        )
        wanted = next((item_id for item_id in preferred if any(c.id == item_id for c in offered)), None)
        selected = wanted or _select_thorough(PLAYED, state, offered)
        provider.selected = (selected,) if selected else ()
        scene_before = state.current_scene_id
        try:
            result = engine.turn(PERSONAS["thorough"])
        except (ProposalValidationError, RuntimeContractError):
            provider.selected = ()
            selected = None
            engine.turn(PERSONAS["thorough"])
        if selected and engine.last_attempt.outcome == "committed":
            journey.picked.append(selected)
        if state.current_scene_id != scene_before:
            journey.scenes.append(state.current_scene_id)
            if state.current_scene_id == "2A":
                journey.entry_texts.extend(segment.text for segment in result.segments)
            if engine.last_attempt.transition_cause in ("forced", "timer"):
                journey.forced_exits.append((scene_before, engine.last_attempt.transition_cause))
    return journey


def _assert_equivalent(preferred: tuple[str, ...]) -> None:
    expected = full_walk(preferred)
    actual = play(preferred)
    assert actual.picked == expected.picked
    assert actual.forced_exits == expected.forced_exits
    assert actual.scenes == expected.scenes
    assert actual.entry_texts == expected.entry_texts
    assert actual.deadline_events == expected.deadline_events
    assert actual.state.turn_index == expected.state.turn_index
    assert sorted(actual.state.facts.asserted, key=str) == sorted(expected.state.facts.asserted, key=str)
    assert actual.state.turn_records == expected.state.turn_records


@pytest.mark.nightly
def test_shared_prefix_matches_an_early_branch() -> None:
    _assert_equivalent(("k_sl_1a_b_r0",))


@pytest.mark.nightly
def test_shared_prefix_matches_a_late_branch() -> None:
    _assert_equivalent(("k_sl_3b_b_r2",))
