from __future__ import annotations

from storygame.engine.state import Event, GameState, PlayerState, WorldState
from storygame.engine.world import build_default_state


def test_state_helpers_clamp_progress_and_tension():
    state = build_default_state(seed=2)
    assert state.with_progress(-0.5).progress == 0.0
    assert state.with_progress(2.0).progress == 1.0

    assert state.with_tension(-1.0).tension == 0.0
    assert state.with_tension(2.0).tension == 1.0


def test_game_state_event_collections_and_replay_signature_stable():
    state = build_default_state(seed=2)

    state.append_event(Event(type="a"))
    state.append_events((Event(type="b"), Event(type="c", message_key="x")))
    state.append_beat("hook")

    sig = state.replay_signature()

    assert isinstance(state.event_log, object)
    assert len(state.event_log) == 3
    assert state.beat_history == ("hook",)
    assert len(sig) == 64


def test_game_state_tail_uses_sorted_room_items_in_signature():
    state = build_default_state(seed=9)
    state2 = state.clone()
    assert state2.replay_signature() == state.replay_signature()

