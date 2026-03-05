from __future__ import annotations

from random import Random

import pytest

from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.persistence.savegame_sqlite import SqliteSaveStore


def _event_for_test() -> Event:
    return Event(
        type="plot",
        message_key="test_event",
        turn_index=4,
        delta_progress=0.1,
        delta_tension=0.05,
    )


def test_save_and_load_roundtrip_preserves_state_and_rng(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=12)
    state.progress = 0.41
    state.tension = 0.55
    state.turn_index = 4
    state.player.inventory = ("torch", "bronze_key")
    state.append_event(_event_for_test())

    rng = Random(1234)
    rng.random()
    rng.random()

    with SqliteSaveStore(db_path) as store:
        store.save_run(
            "demo",
            state,
            rng,
            raw_command="north",
            action_kind="move",
            beat_type="inciting_incident",
            template_key="incite_template",
        )
        loaded_state, loaded_rng = store.load_run("demo")

    assert loaded_state.replay_signature() == state.replay_signature()
    assert loaded_rng.getstate() == rng.getstate()


def test_load_nonexistent_slot_raises_value_error(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    with SqliteSaveStore(db_path) as store, pytest.raises(ValueError, match="No save exists"):
        store.load_run("missing")


def test_list_slots_returns_sorted_slots(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    with SqliteSaveStore(db_path) as store:
        state = build_default_state(seed=1)
        rng = Random(1)
        store.save_run("z", state, rng)
        store.save_run("a", state, rng)
        store.save_run("m", state, rng)

    with SqliteSaveStore(db_path) as store:
        assert store.list_slots() == ["a", "m", "z"]
