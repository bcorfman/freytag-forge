from __future__ import annotations

import json
from random import Random

import pytest

from storygame.cli import run_turn
from storygame.engine.facts import apply_fact_ops
from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.persistence.savegame_sqlite import SqliteSaveStore, deserialize_state, serialize_state
from tests.narrator_stubs import StubNarrator


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
    state.pending_high_impact_command = "punch police officer"
    state.pending_high_impact_assessment = {"impact_class": "critical", "score": 1.8}

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
    assert loaded_state.pending_high_impact_command == "punch police officer"
    assert loaded_state.pending_high_impact_assessment["impact_class"] == "critical"
    assert loaded_rng.getstate() == rng.getstate()


def test_save_and_load_roundtrip_prefers_fact_backed_active_goal(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=13, genre="mystery")
    state.active_goal = "stale in-memory goal"
    state.world_facts.assert_fact("active_goal", "Review the route key and question Daria.")

    with SqliteSaveStore(db_path) as store:
        store.save_run("goal_slot", state, Random(44))
        loaded_state, _loaded_rng = store.load_run("goal_slot")

    assert loaded_state.active_goal == "Review the route key and question Daria."
    assert loaded_state.world_facts.holds("active_goal", "Review the route key and question Daria.")


def test_save_and_load_roundtrip_prefers_fact_backed_player_projection_data(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=14, genre="mystery")
    destination = next(room_id for room_id in state.world.rooms if room_id != state.player.location)
    item_id = next(item_id for item_id in state.world.items if item_id not in state.player.inventory)

    apply_fact_ops(
        state,
        [
            {"op": "assert", "fact": ("at", "player", destination)},
            {"op": "assert", "fact": ("holding", "player", item_id)},
            {"op": "assert", "fact": ("flag", "player", "fact_backed_position")},
        ],
    )

    with SqliteSaveStore(db_path) as store:
        store.save_run("projection_slot", state, Random(45))
        row = store.conn.execute("SELECT payload FROM state_snapshots WHERE slot = ?", ("projection_slot",)).fetchone()
        assert row is not None
        payload = json.loads(str(row["payload"]))

    payload["player"]["location"] = "stale_room"
    payload["player"]["inventory"] = []
    payload["player"]["flags"] = {"stale_flag": True}
    payload["room_items"] = {room_id: [] for room_id in state.world.rooms}

    loaded_state = deserialize_state(payload)

    assert loaded_state.player.location == destination
    assert item_id in loaded_state.player.inventory
    assert loaded_state.player.flags.get("fact_backed_position") is True
    assert loaded_state.player.flags.get("stale_flag") is not True


def test_serialize_state_canonicalizes_stale_player_inventory_before_persistence() -> None:
    state = build_default_state(seed=15, genre="thriller")
    extra_item = next(item_id for item_id in state.world.items if item_id not in state.player.inventory)
    state.player.inventory = state.player.inventory + (extra_item,)

    payload = serialize_state(state)

    assert ["holding", "player", extra_item] in payload["world_facts"]


def test_deserialize_state_can_rebuild_fact_backed_projection_from_legacy_payload() -> None:
    state = build_default_state(seed=16, genre="mystery")
    destination = next(room_id for room_id in state.world.rooms if room_id != state.player.location)
    item_id = next(item_id for item_id in state.world.items if item_id not in state.player.inventory)
    payload = serialize_state(state)
    payload["world_facts"] = []
    payload["active_goal"] = "Question the witness in the next room."
    payload["player"] = {
        "location": destination,
        "inventory": [item_id],
        "flags": {"legacy_loaded": True},
    }
    payload["room_items"] = {room_id: [] for room_id in state.world.rooms}
    payload["last_judge_decision"] = {
        "decision_id": "judge-1",
        "status": "accepted",
        "judge": "critic",
        "rationale": "looks good",
    }
    payload["pending_high_impact_command"] = "break the pact"
    payload["pending_high_impact_assessment"] = {"impact_class": "critical"}

    loaded_state = deserialize_state(payload)

    assert loaded_state.player.location == destination
    assert loaded_state.player.inventory == (item_id,)
    assert loaded_state.player.flags["legacy_loaded"] is True
    assert loaded_state.active_goal == "Question the witness in the next room."
    assert loaded_state.world_facts.holds("at", "player", destination)
    assert loaded_state.world_facts.holds("holding", "player", item_id)
    assert loaded_state.world_facts.holds("flag", "player", "legacy_loaded")
    assert loaded_state.last_judge_decision["decision_id"] == "judge-1"
    assert loaded_state.pending_high_impact_command == "break the pact"


def test_deserialize_state_handles_absent_judge_decision_and_pending_assessment() -> None:
    payload = serialize_state(build_default_state(seed=17, genre="thriller"))
    payload["world_facts"] = []
    payload["last_judge_decision"] = None
    payload["pending_high_impact_assessment"] = "ignored"

    loaded_state = deserialize_state(payload)

    assert loaded_state.last_judge_decision is None
    assert loaded_state.pending_high_impact_assessment == {}


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

        from storygame.cli import run_turn

        rng = Random(rng_seed)
        state = build_default_state(seed=rng_seed)
        _ignored = StubNarrator()

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
        narrator = StubNarrator()

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
