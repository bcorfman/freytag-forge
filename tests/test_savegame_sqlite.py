from __future__ import annotations

import json
from random import Random

import pytest

from storygame.cli import MockNarrator, run_turn
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
    state = build_default_state(seed=12, genre="thriller", session_length="long")
    state.progress = 0.41
    state.tension = 0.55
    state.turn_index = 4
    inventory_seed = tuple(state.world.items.keys())[:2]
    state.player.inventory = inventory_seed
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
    assert loaded_state.story_genre == "thriller"
    assert loaded_state.session_length == "long"
    assert loaded_state.plot_curve_id == state.plot_curve_id
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


def test_load_resume_replays_deterministically_with_post_load_commands(tmp_path):
    db_path = tmp_path / "saves.sqlite"

    seed = 18
    pre_save_commands = ["go north", "look", "inventory", "look"]
    distraction_commands = ["look", "inventory"]
    continuation_commands = ["look", "north", "look", "inventory", "look"]

    def _run_without_save(commands: list[str], rng_seed: int) -> tuple[str, tuple]:
        from random import Random

        from storygame.cli import MockNarrator as _IgnoredNarrator
        from storygame.cli import run_turn

        rng = Random(rng_seed)
        state = build_default_state(seed=rng_seed)
        _ignored = _IgnoredNarrator()

        for command in commands:
            state, _lines, _action_raw, _beat, _continued = run_turn(
                state,
                command,
                rng,
                _ignored,
            )

        return state.replay_signature(), rng.getstate()

    expected_signature, expected_rng = _run_without_save(pre_save_commands + continuation_commands, seed)

    with SqliteSaveStore(db_path) as store:
        rng = Random(seed)
        state = build_default_state(seed=seed)
        narrator = MockNarrator()

        for command in pre_save_commands:
            state, _lines, _action_raw, _beat, _continued = run_turn(
                state,
                command,
                rng,
                narrator,
                save_store=store,
            )
            assert _continued

        state, _lines, _action_raw, _beat, _continued = run_turn(
            state,
            "save checkpoint",
            rng,
            narrator,
            save_store=store,
        )
        assert "Saved to slot 'checkpoint'." in _lines

        for command in distraction_commands:
            state, _lines, _action_raw, _beat, _continued = run_turn(
                state,
                command,
                rng,
                narrator,
                save_store=store,
            )
            assert _continued

        state, _lines, _action_raw, _beat, _continued = run_turn(
            state,
            "load checkpoint",
            rng,
            narrator,
            save_store=store,
        )
        assert "Loaded from slot 'checkpoint'." in _lines

        for command in continuation_commands:
            state, _lines, _action_raw, _beat, _continued = run_turn(
                state,
                command,
                rng,
                narrator,
                save_store=store,
            )
            assert _continued

    assert state.replay_signature() == expected_signature
    assert rng.getstate() == expected_rng


def test_save_run_writes_story_state_artifacts(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=55)
    state.progress = 0.72
    state.player.flags["talked_guide"] = True
    state.append_event(_event_for_test())

    with SqliteSaveStore(db_path) as store:
        store.save_run("artifact slot", state, Random(99))

    artifact_dir = db_path.parent / "story_artifacts" / "artifact_slot"
    story_state_path = artifact_dir / "StoryState.json"
    story_path = artifact_dir / "STORY.md"

    assert story_state_path.exists()
    assert story_path.exists()

    payload = json.loads(story_state_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] >= 2
    assert payload["seed"] == 55
    assert payload["player"]["flags"]["talked_guide"] is True
    assert payload["trace"]["judge_decision"]["status"] == "accepted"
    assert payload["story_markdown_sha256"]

    markdown = story_path.read_text(encoding="utf-8")
    assert "# StoryState Workspace" in markdown
    assert "Talked" in markdown or "talked_guide" in markdown
