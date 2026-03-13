from __future__ import annotations

import builtins
from pathlib import Path
from random import Random

import pytest

from storygame import cli as cli_module
from storygame.cli import (
    _build_narrator,
    _joined_with_and,
    _lowercase_location_phrase,
    _opening_story_editor,
    _public_event_message,
    _sanitize_narration_for_player,
    _setup_phase_lines,
    _with_indefinite_article,
    main,
    run_replay,
    run_turn,
)
from storygame.engine.world import build_default_state
from tests.narrator_stubs import StubNarrator


class _PassThroughEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return lines

    def review_turn(self, lines, active_goal, turn_index, debug=False):  # noqa: ANN001
        return lines


class _StubSetupDirector:
    def compose_opening(self, state):  # noqa: ANN001
        return list(state.world_package.get("story_plan", {}).get("setup_paragraphs", ()))

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001
        return lines


class _RaisingSaveStore:
    def save_run(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("boom-save")

    def load_run(self, slot: str):  # noqa: ARG002
        raise RuntimeError("boom-load")


def test_cli_helper_formatters_and_message_filters() -> None:
    assert _lowercase_location_phrase("") == "the area"
    assert _lowercase_location_phrase("Front Steps") == "the front steps"
    assert _with_indefinite_article("") == ""
    assert _with_indefinite_article("archive key") == "an archive key"
    assert _with_indefinite_article("ledger") == "a ledger"

    edited = _opening_story_editor(
        [
            "Where you are: Front Steps, neutral mystery scene",
            "You were tasked with.",
            "Cast: x",
        ]
    )
    assert any("forced to take one final case" in line.lower() for line in edited)
    assert all("neutral mystery scene" not in line.lower() for line in edited)

    assert _joined_with_and([]) == ""
    assert _joined_with_and(["a"]) == "a"
    assert _joined_with_and(["a", "b"]) == "a and b"
    assert _joined_with_and(["a", "b", "c"]) == "a, b, and c"

    assert _public_event_message("") == ""
    assert _public_event_message("unknown_command").startswith("I didn't understand")
    assert _public_event_message("move_success") == ""
    assert _public_event_message("A human sentence.") == "A human sentence."

    assert _sanitize_narration_for_player("Hook beat at room.", debug=False) == ""
    assert _sanitize_narration_for_player("Hook beat at room.", debug=True) == "Hook beat at room."


def test_build_narrator_invalid_mode_raises() -> None:
    with pytest.raises(ValueError, match="Narrator mode"):
        _build_narrator("invalid")


def test_run_turn_save_and_load_generic_exception_paths() -> None:
    state = build_default_state(seed=701)
    save_store = _RaisingSaveStore()

    _next, lines, _raw, _beat, _continued = run_turn(
        state,
        "save slot1",
        Random(701),
        StubNarrator(),
        save_store=save_store,
        output_editor=_PassThroughEditor(),
        story_director=_StubSetupDirector(),
    )
    assert any("Failed to save" in line for line in lines)

    _next, lines, _raw, _beat, _continued = run_turn(
        state,
        "load slot1",
        Random(701),
        StubNarrator(),
        save_store=save_store,
        output_editor=_PassThroughEditor(),
        story_director=_StubSetupDirector(),
    )
    assert any("Failed to load" in line for line in lines)


def test_run_replay_breaks_on_quit_branch() -> None:
    end_state = run_replay(seed=702, commands=["quit", "look"], narrator=StubNarrator())
    assert end_state.turn_index == 0


def test_setup_phase_lines_uses_default_director(monkeypatch) -> None:
    state = build_default_state(seed=703)
    monkeypatch.setattr(cli_module, "StoryDirector", lambda mode: _StubSetupDirector())  # noqa: ARG005
    lines = _setup_phase_lines(state)
    assert len(lines) >= 3


def test_main_covers_default_transcript_and_autosave_paths(tmp_path, monkeypatch) -> None:
    replay_path = tmp_path / "commands.txt"
    replay_path.write_text("look\n", encoding="utf-8")
    autosave_db = tmp_path / "autosave.sqlite"

    monkeypatch.setattr(cli_module, "_build_narrator", lambda mode: StubNarrator())  # noqa: ARG005
    monkeypatch.setattr(cli_module, "build_output_editor", lambda mode: _PassThroughEditor())  # noqa: ARG005
    monkeypatch.setattr(cli_module, "StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005

    main(
        [
            "--seed",
            "7",
            "--replay",
            str(replay_path),
            "--autosave-slot",
            "auto",
            "--save-db",
            str(autosave_db),
        ]
    )
    default_transcript = Path("runs") / "replay_seed_7.txt"
    assert default_transcript.exists()
    default_transcript.unlink()

    inputs = iter(["look", "quit"])
    transcript = tmp_path / "live.txt"
    monkeypatch.setattr(builtins, "input", lambda _=None: next(inputs))
    main(
        [
            "--seed",
            "8",
            "--transcript",
            str(transcript),
            "--autosave-slot",
            "auto",
            "--save-db",
            str(autosave_db),
        ]
    )
    assert transcript.exists()
