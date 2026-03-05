from random import Random

from storygame.engine.events import select_event
from storygame.engine.world import build_default_state
from storygame.plot.beat_manager import Beat, select_beat


def test_select_beat_deterministic_with_seed():
    state = build_default_state(5)
    state.progress = 0.72
    state.beat_history = ("confrontation",)
    beat_one = select_beat(state, Random(11))
    beat_two = select_beat(state, Random(11))

    assert beat_one == beat_two


def test_select_event_matches_tags():
    state = build_default_state(5)
    state.progress = 0.72
    beat = Beat(type="irreversible_choice", tags=("irreversible_choice", "climax"))
    event_one = select_event(beat, state, Random(44))
    event_two = select_event(beat, state, Random(44))

    assert event_one == event_two
    assert "irreversible_choice" in event_one.tags or "climax" in event_one.tags
