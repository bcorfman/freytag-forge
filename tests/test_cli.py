from __future__ import annotations

import builtins
from random import Random

from storygame.cli import main, run_replay, run_turn, _build_narrator, _event_lines, _write_transcript_line
from storygame.cli import _room_lines
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.engine.parser import parse_command
from storygame.engine.state import Room
from storygame.llm.context import build_narration_context
from storygame.engine.world import build_default_state
from storygame.llm.adapters import MockNarrator, SilentNarrator


def test_cli_helpers_handle_empty_event_list_and_no_transcript():
    assert _event_lines([]) == ""

    line = _room_lines(build_default_state(seed=1))
    assert line.startswith("[Harbor Steps]")

    _write_transcript_line(None, "ignored")


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


def test_main_plays_input_loop_and_stops_on_quit(tmp_path, monkeypatch):
    replay = ["look", "quit"]
    inputs = iter(replay)
    transcript = tmp_path / "game.txt"

    monkeypatch.setattr(builtins, "input", lambda _=None: next(inputs))

    main(["--seed", "1", "--transcript", str(transcript)])

    text = transcript.read_text()
    assert "CMD look" in text
    assert "CMD quit" in text
    assert "Goodbye." in text


def test_main_debug_replay_prints_debug_lines(tmp_path):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\n")

    main([
        "--seed",
        "1",
        "--replay",
        str(replay),
        "--debug",
        "--transcript",
        str(transcript),
    ])

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
