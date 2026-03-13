from __future__ import annotations

import builtins
from contextlib import suppress
from io import StringIO
from random import Random

from rich.console import Console

from storygame.cli import (
    _build_memory_tag_set,
    _build_narrator,
    _emit_cli_line,
    _event_lines,
    _room_distance,
    _room_lines,
    _setup_phase_lines,
    _signal_hint,
    _write_transcript_line,
    main,
    run_replay,
    run_turn,
)
from storygame.engine.parser import parse_command
from storygame.engine.state import Room
from storygame.engine.world import build_default_state
from storygame.llm.adapters import OpenAIAdapter, SilentNarrator
from storygame.llm.context import build_narration_context
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.persistence.story_state import STORY_STATE_FILE, load_story_state_payload
from tests.narrator_stubs import StubNarrator


class _StubSetupDirector:
    def compose_opening(self, state):  # noqa: ANN001
        return list(state.world_package.get("story_plan", {}).get("setup_paragraphs", ()))

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001
        return lines


def test_cli_helpers_handle_empty_event_list_and_no_transcript():
    assert _event_lines([]) == ""

    state = build_default_state(seed=1)
    line = _room_lines(state)
    assert line.startswith(f"{state.world.rooms[state.player.location].name}\n")

    _write_transcript_line(None, "ignored")


def test_emit_cli_line_wraps_long_lines_to_console_width():
    output = StringIO()
    console = Console(file=output, width=24, force_terminal=False, color_system=None)

    _emit_cli_line(console, "Freytag Forge should wrap this line cleanly.")

    wrapped_lines = [line for line in output.getvalue().splitlines() if line]
    assert len(wrapped_lines) >= 2
    assert all(len(line) <= 24 for line in wrapped_lines)


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
    assert "- Witness account:" not in text

    debug_text = _event_lines(events, debug=True)
    assert "move_success" in debug_text
    assert "talk:" in debug_text


def test_room_lines_when_empty_room_has_no_optional_sections():
    state = build_default_state(seed=1)
    room_id = state.player.location
    state.world.rooms[room_id] = Room(
        id=room_id,
        name="Harbor",
        description="Closed.",
    )
    lines = _room_lines(state)
    assert lines == "Harbor\nClosed."


def test_run_replay_executes_sequence_with_stub_narrator():
    final_state = run_replay(seed=13, commands=["look", "inventory"], debug=True, narrator=StubNarrator())
    assert final_state.turn_index == 2


def test_run_replay_selects_curve_from_genre_and_length():
    final_state = run_replay(
        seed=13,
        commands=["look"],
        genre="horror",
        session_length="short",
        tone="dark",
        debug=False,
        narrator=StubNarrator(),
    )
    assert final_state.story_genre == "horror"
    assert final_state.session_length == "short"
    assert final_state.story_tone == "dark"
    assert final_state.plot_curve_id in {"horror_monster_house", "horror_psychological_haunting"}
    assert final_state.story_outline_id


def test_build_narrator_modes():
    narrator = _build_narrator("openai")
    assert isinstance(narrator, OpenAIAdapter)
    state = build_default_state(seed=1)
    context = build_narration_context(state, parse_command("look"), "hook")
    with suppress(RuntimeError):
        narrator.generate(context)


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
        StubNarrator(),
    )
    assert action_raw == ""
    assert continued is False
    assert lines == ["Goodbye."]


def test_signal_hint_and_room_distance_cover_missing_graph_cases():
    state = build_default_state(seed=16)
    start_room = state.player.location
    assert _room_distance(state, start_room, start_room) == 0
    assert _room_distance(state, start_room, "nonexistent") is None

    no_exit_state = build_default_state(seed=16)
    room = no_exit_state.world.rooms[no_exit_state.player.location]
    original_exits = room.exits
    try:
        room.exits = {}
        assert _signal_hint(no_exit_state) == ""
    finally:
        room.exits = original_exits

    hint_state = build_default_state(seed=16)
    hint = _signal_hint(hint_state)
    assert isinstance(hint, str)


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
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    tags = _build_memory_tag_set(state, parse_command(f"talk {npc_id}"))
    assert "beat_unknown" in tags
    assert any(tag.startswith("goal_") for tag in tags)
    assert npc_id in tags
    assert f"npc_{npc_id}" in tags


def test_run_replay_with_all_stores_runs_to_completion(tmp_path):
    initial_state = build_default_state(seed=21)
    final_state = run_replay(
        seed=21,
        commands=["look", "save quicksave", "north", "load quicksave"],
        save_db=tmp_path / "saves.sqlite",
        memory_db=tmp_path / "memory.sqlite",
    )
    assert final_state.player.location == initial_state.player.location


def test_first_turn_uses_diegetic_room_first_output():
    state = build_default_state(seed=15)
    next_state, lines, _action_raw, _beat, continued = run_turn(
        state,
        "look",
        Random(15),
        SilentNarrator(),
    )

    assert continued is True
    assert next_state.turn_index == 1
    assert lines[0].startswith(f"{state.world.rooms[state.player.location].name}\n")
    assert all("Before dawn" not in line for line in lines)
    assert all(not line.startswith("- ") for line in lines)


def test_main_plays_input_loop_and_stops_on_quit(tmp_path, monkeypatch):
    replay = ["look", "quit"]
    inputs = iter(replay)
    transcript = tmp_path / "game.txt"

    monkeypatch.setattr(builtins, "input", lambda _=None: next(inputs))
    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005

    main(["--seed", "1", "--transcript", str(transcript)])

    text = transcript.read_text()
    assert "Before dawn" not in text
    assert ">LOOK" in text
    assert ">QUIT" in text
    assert "Goodbye." in text


def test_main_debug_replay_prints_debug_lines(tmp_path, monkeypatch):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\n")

    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
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
            StubNarrator(),
            save_store=store,
        )
        assert action_raw == "save checkpoint"
        assert "Saved to slot 'checkpoint'." in lines

        direction = sorted(state.world.rooms[state.player.location].exits.keys())[0]
        destination = state.world.rooms[state.player.location].exits[direction]
        state, _, _action, _beat, _continued = run_turn(
            state,
            direction,
            rng,
            StubNarrator(),
            save_store=store,
        )
        assert state.player.location == destination

        state, lines, _action, _beat, _continued = run_turn(
            state,
            "load checkpoint",
            rng,
            StubNarrator(),
            save_store=store,
        )

        assert state.replay_signature() == saved_signature
        assert "Loaded from slot 'checkpoint'." in lines
        assert rng.random() == baseline.random()


def test_main_save_and_load_via_cli(tmp_path, monkeypatch):
    db_path = tmp_path / "saves.sqlite"
    transcript = tmp_path / "game.txt"
    replay = tmp_path / "commands.txt"
    replay.write_text("save demo\nnorth\nload demo\nquit\n")

    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
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
        StubNarrator(),
        debug=True,
    )

    assert any("[debug] judge_status=" in line for line in lines)


def test_run_turn_debug_includes_coherence_budget_telemetry():
    state = build_default_state(seed=24)
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(24),
        StubNarrator(),
        debug=True,
    )

    assert any("[debug] coherence_budget" in line for line in lines)


def test_run_turn_unknown_input_routes_to_freeform_roleplay_and_updates_flags():
    state = build_default_state(seed=88)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        f"ask {npc_id} about the signal",
        Random(88),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert any(npc_id in line.lower() for line in lines)
    assert not any("didn't understand" in line.lower() for line in lines)
    assert next_state.player.flags.get(f"asked_signal_{npc_id}") is True


def test_run_turn_freeform_rejects_unreachable_target_without_fact_updates():
    state = build_default_state(seed=89)
    initial_flags = dict(state.player.flags)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "ask dragon about the signal",
        Random(89),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert any("no one here" in line.lower() for line in lines)
    assert next_state.player.flags == initial_flags


def test_run_turn_blocks_high_impact_action_until_player_confirms() -> None:
    state = build_default_state(seed=96)
    next_state, lines, action_raw, beat_type, continued = run_turn(
        state,
        "punch police officer",
        Random(96),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert beat_type == "impact_gate"
    assert action_raw == "punch police officer"
    assert next_state.turn_index == 0
    assert next_state.pending_high_impact_command == "punch police officer"
    assert "impact_class" in next_state.pending_high_impact_assessment
    assert any("type proceed" in line.lower() for line in lines)


def test_run_turn_high_impact_confirmation_supports_cancel_and_proceed() -> None:
    state = build_default_state(seed=97)
    state, _lines, _action_raw, _beat_type, _continued = run_turn(
        state,
        "punch police officer",
        Random(97),
        SilentNarrator(),
        debug=False,
    )

    canceled_state, cancel_lines, _cancel_raw, cancel_beat, _cancel_continued = run_turn(
        state,
        "cancel",
        Random(97),
        SilentNarrator(),
        debug=False,
    )
    assert cancel_beat == "impact_gate"
    assert canceled_state.pending_high_impact_command == ""
    assert any("canceled" in line.lower() for line in cancel_lines)

    warned_state, _warn_lines, _warn_raw, _warn_beat, _warn_continued = run_turn(
        state,
        "punch police officer",
        Random(97),
        SilentNarrator(),
        debug=False,
    )
    proceeded_state, proceed_lines, _proceed_raw, proceed_beat, proceed_continued = run_turn(
        warned_state,
        "proceed",
        Random(97),
        SilentNarrator(),
        debug=False,
    )

    assert proceed_continued is True
    assert proceed_beat == "freeform_roleplay"
    assert proceeded_state.turn_index == 1
    assert proceeded_state.pending_high_impact_command == ""
    assert proceeded_state.player.flags.get("story_replan_required") is True
    assert any(event.type == "major_disruption" for event in proceeded_state.event_log.events)
    assert any("planned arc" in line.lower() for line in proceed_lines)


def test_run_turn_triggers_story_replan_on_followup_turn_after_major_disruption() -> None:
    state = build_default_state(seed=98)
    state, _warn_lines, _warn_raw, _warn_beat, _warn_continued = run_turn(
        state,
        "punch police officer",
        Random(98),
        SilentNarrator(),
        debug=False,
    )
    state, _proceed_lines, _proceed_raw, _proceed_beat, _proceed_continued = run_turn(
        state,
        "proceed",
        Random(98),
        SilentNarrator(),
        debug=False,
    )
    assert state.player.flags.get("story_replan_required") is True
    prior_goal = state.active_goal

    replanned_state, replanned_lines, _raw, _beat, continued = run_turn(
        state,
        "look",
        Random(98),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert replanned_state.player.flags.get("story_replan_required") is False
    assert replanned_state.active_goal != prior_goal
    assert any(event.type == "story_replan" for event in replanned_state.event_log.events)
    assert any("story shifts" in line.lower() for line in replanned_lines)


def test_run_turn_applies_output_editor_before_returning_lines():
    class _PassThroughEditor:
        def review_opening(self, lines, active_goal):  # noqa: ANN001
            return lines

        def review_turn(self, lines, active_goal, turn_index, debug=False):  # noqa: ANN001
            return [line.replace("Echoes", "Edited echoes") for line in lines]

    state = build_default_state(seed=93)
    next_state, lines, _action_raw, _beat, continued = run_turn(
        state,
        "look",
        Random(93),
        SilentNarrator(),
        output_editor=_PassThroughEditor(),
    )

    assert continued is True
    assert next_state.turn_index == 1
    assert any("edited echoes" in line.lower() for line in lines)


def test_setup_phase_lines_include_who_where_and_objective():
    state = build_default_state(seed=90, genre="fantasy", tone="epic")
    lines = _setup_phase_lines(state, _StubSetupDirector())

    assert 3 <= len(lines) <= 4
    protagonist = str(state.world_package.get("story_plan", {}).get("protagonist_name", "")).lower()
    assert any(protagonist in paragraph.lower() for paragraph in lines)
    assert any("objective" in paragraph.lower() for paragraph in lines)
    assert all(not paragraph.lower().startswith("where you are:") for paragraph in lines)
    assert all(not paragraph.lower().startswith("cast:") for paragraph in lines)
    assert all("immediate objective:" not in paragraph.lower() for paragraph in lines)
    assert all("the only exit is to" not in paragraph.lower() for paragraph in lines)
    assert any("case file" in paragraph.lower() or state.active_goal in paragraph for paragraph in lines)


def test_setup_phase_lines_story_editor_removes_legacy_meta_fragments():
    state = build_default_state(seed=91, genre="mystery", tone="neutral")
    lines = _setup_phase_lines(state, _StubSetupDirector())
    joined = "\n".join(lines).lower()

    assert "neutral mystery scene" not in joined
    assert "move the story toward resolution" not in joined
    assert "where you are:" not in joined
    assert "cast:" not in joined
    assert "tasked with." not in joined


def test_setup_phase_lines_place_identity_after_environment_and_use_named_contact():
    state = build_default_state(seed=123, genre="mystery", tone="dark")
    lines = _setup_phase_lines(state, _StubSetupDirector())
    assert len(lines) >= 3

    first = lines[0].lower()
    joined = "\n".join(lines).lower()

    assert "you are " not in joined
    assert "has kept a low profile" in first
    assert "premise waits nearby" not in joined
    assert "premise:" not in joined


def test_setup_phase_lines_weave_background_and_actionable_objective():
    state = build_default_state(seed=124, genre="mystery", tone="dark")
    lines = _setup_phase_lines(state, _StubSetupDirector())
    joined = "\n".join(lines).lower()

    assert "the case in front of you starts simply" not in joined
    assert "low profile" in joined
    assert "first practical objective" in joined


def test_main_replay_emits_setup_phase_before_commands(tmp_path, monkeypatch):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\n", encoding="utf-8")

    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
    main(["--seed", "4", "--replay", str(replay), "--transcript", str(transcript)])

    lines = transcript.read_text(encoding="utf-8").splitlines()
    command_index = next(i for i, line in enumerate(lines) if line == ">LOOK")
    assert command_index >= 3


def test_save_persists_last_accepted_judge_decision(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=77)
    rng = Random(77)
    state.last_judge_decision = {
        "decision_id": "judge-test-accepted",
        "status": "accepted",
        "judge": "director",
        "rationale": "deterministic test fixture",
    }

    with SqliteSaveStore(db_path) as store:
        _state, save_lines, _action_raw, _beat, _continued = run_turn(
            state,
            "save checkpoint",
            rng,
            StubNarrator(),
            save_store=store,
        )
        assert "Saved to slot 'checkpoint'." in save_lines

    artifact_dir = db_path.parent / "story_artifacts" / "checkpoint"
    payload = load_story_state_payload(artifact_dir / STORY_STATE_FILE)
    assert payload["trace"]["judge_decision"]["decision_id"] == "judge-test-accepted"
    assert payload["trace"]["judge_decision"]["status"] == "accepted"
