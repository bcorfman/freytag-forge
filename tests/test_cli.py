from __future__ import annotations

import builtins
from random import Random

from storygame.cli import (
    _build_memory_tag_set,
    _build_narrator,
    _event_lines,
    _opening_briefing_lines,
    _room_distance,
    _room_lines,
    _signal_hint,
    _write_transcript_line,
    main,
    run_replay,
    run_turn,
)
from storygame.engine.parser import parse_command
from storygame.engine.state import Room
from storygame.engine.world import build_default_state
from storygame.llm.adapters import MockNarrator, SilentNarrator
from storygame.llm.context import build_narration_context
from storygame.persistence.savegame_sqlite import SqliteSaveStore


def test_cli_helpers_handle_empty_event_list_and_no_transcript():
    assert _event_lines([]) == ""

    line = _room_lines(build_default_state(seed=1))
    assert line.startswith("[Harbor Steps]")

    _write_transcript_line(None, "ignored")


def test_event_lines_hide_engine_keys_unless_debug():
    class _Event:
        def __init__(self, event_type: str, message_key: str) -> None:
            self.type = event_type
            self.message_key = message_key

    events = [
        _Event("move", "move_success"),
        _Event("talk", "Witness account: follow the ledger trail."),
    ]

    text = _event_lines(events)
    assert "move_success" not in text
    assert "Witness account:" in text
    assert "talk:" not in text

    debug_text = _event_lines(events, debug=True)
    assert "move_success" in debug_text
    assert "talk:" in debug_text


def test_opening_briefing_explains_stakes_and_conspiracy():
    state = build_default_state(seed=1)
    lines = _opening_briefing_lines(state)

    assert any("conspiracy" in line.lower() for line in lines)
    assert any("forged" in line.lower() for line in lines)
    assert any("mentor" in line.lower() for line in lines)


def test_room_lines_when_empty_room_has_no_optional_sections():
    state = build_default_state(seed=1)
    state.world.rooms["harbor"] = Room(
        id="harbor",
        name="Harbor",
        description="Closed.",
    )
    lines = _room_lines(state)
    assert lines == "[Harbor]\nClosed."


def test_run_replay_executes_sequence_with_mock_narrator():
    final_state = run_replay(seed=13, commands=["look", "inventory"], debug=True)
    assert final_state.turn_index == 2


def test_build_narrator_modes():
    narrator = _build_narrator("none")
    assert isinstance(narrator, SilentNarrator)
    state = build_default_state(seed=1)
    context = build_narration_context(state, parse_command("look"), "hook")
    assert narrator.generate(context) == ""


def test_run_turn_handles_quit_and_narration_failures():
    state = build_default_state(seed=8)

    class _BadNarrator:
        def generate(self, _context) -> str:
            raise RuntimeError("broken")

    next_state, lines, action_raw, _beat, continued = run_turn(
        state,
        "look",
        Random(8),
        _BadNarrator(),
    )
    assert next_state is not None
    assert any("Narrator failed" in line for line in lines)
    assert action_raw == "look"

    _, lines, action_raw, _beat, continued = run_turn(
        next_state,
        "quit",
        Random(8),
        MockNarrator(),
    )
    assert action_raw == ""
    assert continued is False
    assert lines == ["Goodbye."]


def test_signal_hint_and_room_distance_cover_missing_graph_cases():
    state = build_default_state(seed=16)
    assert _room_distance(state, "harbor", "harbor") == 0
    assert _room_distance(state, "harbor", "nonexistent") is None

    harbor_state = build_default_state(seed=16)
    harbor = harbor_state.world.rooms["harbor"]
    original_exits = harbor.exits
    try:
        harbor.exits = {}
        assert _signal_hint(harbor_state) == ""
    finally:
        harbor.exits = original_exits

    missing_source = build_default_state(seed=16)
    del missing_source.world.rooms["sanctuary"]
    assert _signal_hint(missing_source) == ""

    missing_source.player.location = "harbor"
    assert _signal_hint(missing_source) == ""

    near_sanctuary = build_default_state(seed=16)
    near_sanctuary.player.location = "harbor"
    assert "stronger toward" in _signal_hint(near_sanctuary)


def test_run_turn_save_load_error_paths():
    state = build_default_state(seed=17)
    _, no_store_save_lines, *_ = run_turn(
        state,
        "save quicksave",
        Random(17),
        SilentNarrator(),
        save_store=None,
    )
    assert any("Save requires --save-db" in line for line in no_store_save_lines)

    _, no_store_load_lines, *_ = run_turn(
        state,
        "load missing",
        Random(17),
        SilentNarrator(),
        save_store=None,
    )
    assert any("Load requires --save-db" in line for line in no_store_load_lines)


def test_run_turn_load_missing_slot_with_store_is_handled(tmp_path):
    with SqliteSaveStore(tmp_path / "game.sqlite") as store:
        _, load_lines, *_ = run_turn(
            build_default_state(seed=18),
            "load missing",
            Random(18),
            SilentNarrator(),
            save_store=store,
        )
        assert any("Could not load slot 'missing'" in line for line in load_lines)


def test_build_memory_tag_set_includes_expected_fields():
    state = build_default_state(seed=20)
    tags = _build_memory_tag_set(state, parse_command("talk ferryman"))
    assert "beat_unknown" in tags
    assert "goal_map" in tags
    assert "ferryman" in tags
    assert "npc_ferryman" in tags


def test_run_replay_with_all_stores_runs_to_completion(tmp_path):
    final_state = run_replay(
        seed=21,
        commands=["look", "save quicksave", "north", "load quicksave"],
        save_db=tmp_path / "saves.sqlite",
        memory_db=tmp_path / "memory.sqlite",
    )
    assert final_state.player.location == "harbor"


def test_first_turn_includes_opening_briefing_lines():
    state = build_default_state(seed=15)
    next_state, lines, _action_raw, _beat, continued = run_turn(
        state,
        "look",
        Random(15),
        SilentNarrator(),
    )

    assert continued is True
    assert next_state.turn_index == 1
    assert any("Before dawn" in line for line in lines)
    assert any("mentor" in line.lower() for line in lines)


def test_main_plays_input_loop_and_stops_on_quit(tmp_path, monkeypatch):
    replay = ["look", "quit"]
    inputs = iter(replay)
    transcript = tmp_path / "game.txt"

    monkeypatch.setattr(builtins, "input", lambda _=None: next(inputs))

    main(["--seed", "1", "--transcript", str(transcript)])

    text = transcript.read_text()
    assert "Before dawn" in text
    assert ">LOOK" in text
    assert ">QUIT" in text
    assert "Goodbye." in text


def test_main_debug_replay_prints_debug_lines(tmp_path):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\n")

    main(
        [
            "--seed",
            "1",
            "--replay",
            str(replay),
            "--debug",
            "--transcript",
            str(transcript),
        ]
    )

    assert "[debug] turn=" in transcript.read_text()


def test_run_turn_save_and_load_restore_state(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=7)
    rng = Random(7)
    baseline = Random(7)

    with SqliteSaveStore(db_path) as store:
        saved_signature = state.replay_signature()
        state, lines, action_raw, _beat, _continued = run_turn(
            state,
            "save checkpoint",
            rng,
            MockNarrator(),
            save_store=store,
        )
        assert action_raw == "save checkpoint"
        assert "Saved to slot 'checkpoint'." in lines

        state, _, _action, _beat, _continued = run_turn(
            state,
            "north",
            rng,
            MockNarrator(),
            save_store=store,
        )
        assert state.player.location == "market"

        state, lines, _action, _beat, _continued = run_turn(
            state,
            "load checkpoint",
            rng,
            MockNarrator(),
            save_store=store,
        )

        assert state.replay_signature() == saved_signature
        assert "Loaded from slot 'checkpoint'." in lines
        assert rng.random() == baseline.random()


def test_main_save_and_load_via_cli(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    transcript = tmp_path / "game.txt"
    replay = tmp_path / "commands.txt"
    replay.write_text("save demo\nnorth\nload demo\nquit\n")

    main(
        [
            "--seed",
            "9",
            "--replay",
            str(replay),
            "--transcript",
            str(transcript),
            "--save-db",
            str(db_path),
        ]
    )

    log = transcript.read_text()
    assert "Saved to slot 'demo'." in log
    assert "Loaded from slot 'demo'." in log


def test_run_turn_debug_includes_judge_decision_summary():
    state = build_default_state(seed=23)
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(23),
        MockNarrator(),
        debug=True,
    )

    assert any("[debug] judge_status=" in line for line in lines)


def test_run_turn_debug_includes_coherence_budget_telemetry():
    state = build_default_state(seed=24)
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(24),
        MockNarrator(),
        debug=True,
    )

    assert any("[debug] coherence_budget" in line for line in lines)
