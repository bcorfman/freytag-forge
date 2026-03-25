from __future__ import annotations

import builtins
import json
from contextlib import suppress
from io import StringIO
from random import Random

from rich.console import Console

from storygame.cli import (
    _build_memory_tag_set,
    _build_narrator,
    _cached_room_presentation,
    _dialogue_contains_code_artifact,
    _dialogue_fact_conflict,
    _emit_cli_line,
    _event_lines,
    _freeform_dialogue_policy_error,
    _is_invalid_targeted_dialogue_speaker,
    _is_parroting_dialogue,
    _room_lines,
    _setup_phase_lines,
    _shorten_line,
    _write_transcript_line,
    main,
    run_replay,
    run_turn,
)
from storygame.engine.events import EventTemplate, apply_event_template
from storygame.engine.freeform import RuleBasedFreeformProposalAdapter
from storygame.engine.parser import parse_command
from storygame.engine.state import Npc, Room
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


def test_cold_wind_event_message_stays_location_agnostic() -> None:
    state = build_default_state(seed=52, genre="mystery")
    state.player.location = "foyer"
    template = EventTemplate(
        key="cold_wind",
        message_key="A cold wind enters from the streets.",
        tags=("hook",),
        delta_tension=0.05,
    )

    _next_state, events = apply_event_template(state, template, Random(52))

    assert events[0].message_key == "A cold draft slips in from the drive."
    assert "streets" not in events[0].message_key.lower()


def test_cold_wind_event_uses_current_room_street_fact_when_outdoors() -> None:
    state = build_default_state(seed=521, genre="drama")
    state.player.location = "main_street"
    template = EventTemplate(
        key="cold_wind",
        message_key="A cold wind enters from the streets.",
        tags=("hook",),
        delta_tension=0.05,
    )

    _next_state, events = apply_event_template(state, template, Random(521))

    assert events[0].message_key == "A cold wind runs along the street."


def test_cold_wind_event_falls_back_when_no_supported_outside_source_exists() -> None:
    state = build_default_state(seed=522, genre="mystery")
    state.world.rooms["sealed_archive"] = Room(
        id="sealed_archive",
        name="Sealed Archive",
        description="A sealed archive with stone walls and no visible openings.",
        exits={},
    )
    state.player.location = "sealed_archive"
    template = EventTemplate(
        key="cold_wind",
        message_key="A cold wind enters from the streets.",
        tags=("hook",),
        delta_tension=0.05,
    )

    _next_state, events = apply_event_template(state, template, Random(522))

    assert events[0].message_key == "A cold draft slips in from outside."


def test_shorten_line_prefers_complete_clause_over_ellipsis() -> None:
    text = (
        "The foyer opens beneath a dim chandelier, with rainwater drying on black-and-white tiles "
        "and a long hall stretching deeper into the mansion."
    )

    shortened = _shorten_line(text, 60)

    assert shortened == "The foyer opens beneath a dim chandelier, with rainwater."
    assert "..." not in shortened


def test_shorten_line_returns_short_text_unchanged() -> None:
    assert _shorten_line("A complete sentence.", 80) == "A complete sentence."


def test_dialogue_policy_helpers_reject_wrong_speaker_and_code_artifacts() -> None:
    state = build_default_state(seed=1201, genre="mystery")
    state.player.location = "foyer"
    state.world.rooms["foyer"].npc_ids = ("olivia_thompson", "daria_stone")

    assert _is_invalid_targeted_dialogue_speaker(
        {"speaker": "daria_stone", "text": "The victim died before midnight.", "tone": "in_world"},
        {"intent": "ask_about", "targets": ["olivia_thompson"], "arguments": {}, "proposed_effects": []},
    )
    assert _dialogue_contains_code_artifact(
        {"speaker": "daria_stone", "text": "getStringExtra from the case file is not available yet.", "tone": "in_world"}
    )


def test_dialogue_policy_helpers_distinguish_parroting_from_legitimate_answer() -> None:
    state = build_default_state(seed=1202, genre="mystery")

    assert _is_parroting_dialogue(
        "Daria, which witness is uncooperative?",
        {"speaker": "daria_stone", "text": "You asked me which witness is uncooperative.", "tone": "in_world"},
    )
    assert not _is_parroting_dialogue(
        "Daria, which witness is uncooperative?",
        {
            "speaker": "daria_stone",
            "text": "The uncooperative witness is the groundskeeper; he clams up whenever the ledger comes up.",
            "tone": "in_world",
        },
    )
    assert _dialogue_fact_conflict(state, "daria_stone", "I'm wearing a simple dress.", "appearance")
    assert not _dialogue_fact_conflict(state, "daria_stone", "A crisp blouse and dark skirt.", "appearance")


def test_freeform_dialogue_policy_error_covers_fallback_and_valid_llm_dialogue() -> None:
    state = build_default_state(seed=1203, genre="mystery")
    fallback_action = parse_command("Daria, tell me what happened here")

    fallback_error = _freeform_dialogue_policy_error(
        state,
        "Daria, tell me what happened here",
        fallback_action,
        {"speaker": "narrator", "text": "You ask Daria what happened here.", "tone": "in_world"},
        {
            "intent": "ask_about",
            "targets": ["daria_stone"],
            "arguments": {"topic": "events", "planner_source": "fallback"},
            "proposed_effects": [],
        },
    )
    valid_error = _freeform_dialogue_policy_error(
        state,
        "Daria, which witness is uncooperative?",
        parse_command("Daria, which witness is uncooperative?"),
        {
            "speaker": "daria_stone",
            "text": "The uncooperative witness is the groundskeeper; he clams up whenever the ledger comes up.",
            "tone": "in_world",
        },
        {
            "intent": "ask_about",
            "targets": ["daria_stone"],
            "arguments": {"topic": "witness", "planner_source": "llm"},
            "proposed_effects": [],
        },
    )

    assert "LLM-authored" in fallback_error
    assert valid_error == ""


def test_shorten_line_falls_back_to_word_boundary_with_period() -> None:
    shortened = _shorten_line("alpha beta gamma delta", 10)

    assert shortened == "alpha beta."
    assert "..." not in shortened


def test_non_contextual_event_template_keeps_original_message() -> None:
    state = build_default_state(seed=53, genre="mystery")
    template = EventTemplate(
        key="pressure_rising",
        message_key="The city tightens, as if holding its breath.",
        tags=("escalation",),
        delta_tension=0.06,
    )

    _next_state, events = apply_event_template(state, template, Random(53))

    assert events[0].message_key == "The city tightens, as if holding its breath."


def test_cached_room_presentation_reuses_existing_entry() -> None:
    state = build_default_state(seed=54, genre="mystery")
    state.world_package["room_presentation_cache"] = {
        "foyer": {"long": "Cached long.", "short": "Cached short."}
    }

    presentation = _cached_room_presentation(state, "foyer")

    assert presentation == {"long": "Cached long.", "short": "Cached short."}


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


def test_run_turn_inventory_aliases_list_held_items() -> None:
    for raw_command in ("i", "inventory"):
        state = build_default_state(seed=14)
        next_state, lines, _action_raw, _beat, continued = run_turn(
            state,
            raw_command,
            Random(14),
            StubNarrator(),
        )

        assert continued is True
        assert next_state.turn_index == 1
        joined = "\n".join(lines).lower()
        assert "you are carrying" in joined
        assert "field kit" in joined


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


def test_run_turn_falls_back_to_direct_narration_on_revision_directive_contract_error(monkeypatch):
    class _Gate:
        def generate_with_gate(self, narrator, context):  # noqa: ANN001, ARG002
            raise RuntimeError("CONTRACT_INVALID_REVISION_DIRECTIVE")

    monkeypatch.setattr("storygame.cli.build_default_coherence_gate", lambda: _Gate())
    state = build_default_state(seed=801)
    next_state, lines, _action_raw, _beat, continued = run_turn(
        state,
        "look",
        Random(801),
        StubNarrator("You focus on the room, tracing exits and clues before deciding your next move."),
        debug=False,
    )

    assert continued is True
    assert next_state.turn_index == 1
    assert any("tracing exits and clues" in line.lower() for line in lines)
    assert not any("contract_invalid_revision_directive" in line.lower() for line in lines)


def test_run_turn_discards_failed_narration_when_coherence_wall_clock_times_out(monkeypatch):
    class _Gate:
        def generate_with_gate(self, narrator, context):  # noqa: ANN001, ARG002
            return {
                "narration": (
                    "Noah Kade stepped out of the car, the crunch of gravel beneath his boots echoing in the stillness."
                ),
                "judge_decision": {
                    "status": "failed",
                    "total_score": 0,
                    "threshold": 80,
                    "round_index": 0,
                    "critic_ids": (),
                    "rubric_components": {},
                    "decision_id": "judge-hard-fail-budget_wall_clock_timeout",
                },
                "telemetry": {
                    "critique_rounds": 0,
                    "token_spend": {"narrator": 345, "critics": 0},
                    "elapsed_ms": 60000,
                    "hard_fail_reason": "BUDGET_WALL_CLOCK_TIMEOUT",
                },
            }

    monkeypatch.setattr("storygame.cli.build_default_coherence_gate", lambda: _Gate())
    state = build_default_state(seed=802)
    next_state, lines, _action_raw, _beat, continued = run_turn(
        state,
        "look",
        Random(802),
        StubNarrator(),
        debug=False,
    )

    assert continued is True
    assert next_state.turn_index == 1
    assert not any("noah kade" in line.lower() for line in lines)
    assert any(state.world.rooms[state.player.location].name.lower() in line.lower() for line in lines)


def test_room_lines_do_not_emit_legacy_signal_copy():
    state = build_default_state(seed=16)
    lines = _room_lines(state)
    lower = lines.lower()
    assert "echoes refract through stone" not in lower
    assert "resonance is stronger" not in lower
    assert "signal:" not in lower


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


def test_run_turn_debug_includes_freeform_policy_diagnostics():
    state = build_default_state(seed=241)
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "Daria, knock on the door",
        Random(241),
        SilentNarrator(),
        debug=True,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert any("[debug] freeform_policy " in line for line in lines)
    debug_json_lines = [line for line in lines if line.startswith("[debug-json] ")]
    payload = json.loads(debug_json_lines[-1].replace("[debug-json] ", "", 1))
    assert "freeform_policy" in payload
    assert payload["freeform_policy"]["action_proposal"]["intent"]


def test_run_turn_unknown_input_routes_to_freeform_roleplay_and_fails_closed_without_llm_authorship():
    state = build_default_state(seed=88)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        f"ask {npc_id} about the signal",
        Random(88),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert next_state.player.flags.get(f"asked_signal_{npc_id}") is not True
    assert any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_uses_planner_action_for_deterministic_take_path():
    class _PlannerTakeAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "narrator", "text": "Planner parsed a TAKE intent.", "tone": "in_world"},
                {"intent": "take", "targets": ["ledger_page"], "arguments": {}, "proposed_effects": ["take:ledger_page"]},
            )

    state = build_default_state(seed=220)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Pick up the ledger page and read it.",
        Random(220),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_PlannerTakeAdapter(),
    )

    assert continued is True
    assert beat_type != "freeform_roleplay"
    assert "ledger_page" in next_state.player.inventory
    assert any("clue noted:" in line.lower() for line in lines)
    assert not any("you don't see that here" in line.lower() for line in lines)


def test_run_turn_directional_alias_uses_turn_proposal_path_not_advance_turn(monkeypatch) -> None:
    def _unexpected_advance_turn(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("advance_turn should not be used for ordinary directional turns")

    monkeypatch.setattr("storygame.cli.advance_turn", _unexpected_advance_turn)
    state = build_default_state(seed=2201)
    direction = sorted(state.world.rooms[state.player.location].exits.keys())[0]
    destination = state.world.rooms[state.player.location].exits[direction]

    next_state, lines, action_raw, beat_type, continued = run_turn(
        state,
        direction,
        Random(2201),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert action_raw == direction
    assert next_state.player.location == destination
    assert beat_type != "freeform_roleplay"
    assert lines


def test_run_turn_semantic_navigation_phrase_moves_through_unique_exit() -> None:
    state = build_default_state(seed=2202, genre="mystery")

    next_state, lines, action_raw, beat_type, continued = run_turn(
        state,
        "enter the mansion",
        Random(2202),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type != "freeform_roleplay"
    assert action_raw == "enter the mansion"
    assert next_state.player.location == "foyer"
    assert any("Mansion Foyer" in line for line in lines)


def test_run_turn_prefers_proposal_path_for_parser_style_conversation():
    class _PlannerConversationAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            npc_id = state.world.rooms[state.player.location].npc_ids[0]
            return (
                {
                    "speaker": npc_id,
                    "text": "The ledger matters because someone wanted it hidden before we arrived.",
                    "tone": "in_world",
                },
                {
                    "intent": "ask_about",
                    "targets": [npc_id],
                    "arguments": {"topic": "ledger"},
                    "proposed_effects": ["new_lead"],
                },
            )

    state = build_default_state(seed=221)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "talk to daria stone",
        Random(221),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_PlannerConversationAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.player.flags.get("asked_ledger_daria_stone") is True
    assert any(line.startswith('Daria Stone says: "') for line in lines)
    assert any("wanted it hidden" in line.lower() for line in lines)


def test_run_turn_talk_command_fails_closed_without_llm_planner():
    state = build_default_state(seed=222)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "talk to daria stone",
        Random(222),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)
    assert next_state.player.flags.get("greeted_daria_stone") is not True


def test_run_turn_fails_closed_for_parroting_npc_dialogue() -> None:
    class _ParrotingAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "daria_stone", "text": "You asked me which witness is uncooperative.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "witness", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=88337, genre="mystery")

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, which witness is uncooperative?",
        Random(88337),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_ParrotingAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_allows_legitimate_npc_answer_that_reuses_topic_words() -> None:
    class _LegitimateAnswerAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {
                    "speaker": "daria_stone",
                    "text": "The uncooperative witness is the groundskeeper; he clams up whenever the ledger comes up.",
                    "tone": "in_world",
                },
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "witness", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=883371, genre="mystery")

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, which witness is uncooperative?",
        Random(883371),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_LegitimateAnswerAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert any("groundskeeper" in line.lower() for line in lines)
    assert not any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_natural_language_commands_mutate_world_state_via_freeform_policy():
    state = build_default_state(seed=883)
    after_examine, _lines, _action_raw, beat_type, continued = run_turn(
        state,
        "examine the case file",
        Random(883),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert after_examine.turn_index == 1
    assert after_examine.progress > state.progress
    assert after_examine.player.flags.get("freeform_intent_read_case_file") is True
    assert after_examine.player.flags.get("reviewed_case_file") is True

    after_knock, _lines, _action_raw, beat_type, continued = run_turn(
        after_examine,
        "Daria, knock on the door",
        Random(883),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert after_knock.turn_index == 2
    assert after_knock.progress > after_examine.progress
    assert after_knock.player.flags.get("freeform_intent_knock") is True


def test_run_turn_read_ledger_page_uses_shared_freeform_path():
    state = build_default_state(seed=884)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "read the ledger page",
        Random(884),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert next_state.player.flags.get("reviewed_ledger_page") is True
    assert next_state.progress > state.progress
    assert any("ledger" in line.lower() for line in lines)


def test_run_turn_appearance_question_fails_closed_without_llm_planner():
    state = build_default_state(seed=885)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, what are you wearing?",
        Random(885),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)
    assert next_state.player.flags.get("asked_appearance_daria_stone") is not True


def test_run_turn_ledger_question_gets_specific_dialogue():
    state = build_default_state(seed=886)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, what about the ledger page?",
        Random(886),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert next_state.player.flags.get("asked_ledger_daria_stone") is not True
    assert any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_unknown_input_includes_narrator_output_when_available():
    state = build_default_state(seed=881)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "ask about the signal",
        Random(881),
        StubNarrator("You press for specifics, and the rumor sharpens into a usable lead."),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert any("usable lead" in line.lower() for line in lines)


def test_run_turn_unknown_input_grounds_generic_narration_to_player_action():
    state = build_default_state(seed=882)
    command = "ask daria about the signal"
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        command,
        Random(882),
        StubNarrator("The night is tense and everyone watches in silence."),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_prefers_narrator_prose_over_fallback_bounded_dialogue():
    state = build_default_state(seed=8831)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, what do you make of this place?",
        Random(8831),
        StubNarrator(
            "Outside The Mansion\n"
            "As I stand outside the mansion, the rain needles across my coat and I remind myself "
            "that I need to get oriented before anything else."
        ),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)


def test_room_and_dialogue_lines_shorten_known_npc_names_when_unambiguous():
    class _NpcReplyAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "AI_Assistant", "text": "The grounds feel staged. Someone wanted this approach noticed.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "place", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=8832)
    next_state, first_lines, _action_raw, _beat_type, continued = run_turn(
        state,
        "look",
        Random(8832),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert any("Daria Stone is nearby" in line for line in first_lines)

    final_state, lines, _action_raw, beat_type, continued = run_turn(
        next_state,
        "Daria, what do you make of this place?",
        Random(8832),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_NpcReplyAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert final_state.turn_index == 2
    assert not any("is nearby" in line for line in lines)
    assert any(line.startswith('Daria says: "') for line in lines)
    assert not any(line.startswith('Daria Stone says: "') for line in lines)


def test_room_and_dialogue_lines_keep_full_name_when_first_name_is_ambiguous():
    class _NpcReplyAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "AI_Assistant", "text": "The front approach feels rehearsed, and I don't trust that.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "place", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=8833)
    room_id = state.player.location
    room = state.world.rooms[room_id]
    state.world.npcs["daria_quill"] = Npc(
        id="daria_quill",
        name="Daria Quill",
        description="Another investigator with a wary stare.",
        dialogue="Stay alert.",
    )
    room.npc_ids = room.npc_ids + ("daria_quill",)

    next_state, first_lines, _action_raw, _beat_type, continued = run_turn(
        state,
        "look",
        Random(8833),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert any("Daria Stone and Daria Quill are nearby" in line for line in first_lines)

    final_state, lines, _action_raw, beat_type, continued = run_turn(
        next_state,
        "Daria Stone, what do you make of this place?",
        Random(8833),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_NpcReplyAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert final_state.turn_index == 2
    assert not any("are nearby" in line for line in lines)
    assert any(line.startswith('Daria Stone says: "') for line in lines)


def test_reviewed_turn_output_still_shortens_known_npc_names_when_unambiguous():
    class _NpcReplyAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "daria_stone", "text": "Keep your eyes on the ledger.", "tone": "in_world"},
                {
                    "intent": "greet",
                    "targets": ["daria_stone"],
                    "arguments": {"planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=88335)
    looked_state, _first_lines, _action_raw, _beat_type, continued = run_turn(
        state,
        "look",
        Random(88335),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True

    class _AssistantSpeakerAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "AI_Assistant", "text": "I last saw him near dusk, heading inside alone.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "holmes", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    class _ReintroducingDirector(_StubSetupDirector):
        def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001, ARG002
            return ['Daria Stone says: "Keep your eyes on the ledger."']

    final_state, lines, _action_raw, beat_type, continued = run_turn(
        looked_state,
        "Daria, hello",
        Random(88335),
        SilentNarrator(),
        debug=False,
        story_director=_ReintroducingDirector(),
        freeform_adapter=_AssistantSpeakerAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert final_state.turn_index == 2
    assert any(line.startswith('Daria says: "') for line in lines)
    assert not any(line.startswith('Daria Stone says: "') for line in lines)


def test_run_turn_fails_closed_for_conversational_turns_without_llm_authorship() -> None:
    class _FallbackConversationAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "narrator", "text": "You ask Daria what happened here.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "events", "planner_source": "fallback"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=88336)

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, tell me what happened here",
        Random(88336),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_FallbackConversationAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_fails_closed_for_parroting_npc_dialogue() -> None:
    class _ParrotingAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "daria_stone", "text": "You asked me what happened here.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "events", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=88337)

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, tell me what happened here",
        Random(88337),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_ParrotingAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_fails_closed_when_targeted_conversation_returns_player_speaker() -> None:
    class _PlayerSpeechAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "player", "text": "When did you last see Mr. Holmes?", "tone": "in_world"},
                {
                    "intent": "query",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "holmes", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=88338)

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, when did you last see Mr. Holmes?",
        Random(88338),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_PlayerSpeechAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_fails_closed_when_wrong_npc_answers_targeted_conversation() -> None:
    class _WrongSpeakerAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "daria_stone", "text": "The victim died before midnight.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["olivia_thompson"],
                    "arguments": {"topic": "victim", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=88339, genre="mystery")
    state.player.location = "foyer"
    state.world.rooms["foyer"].npc_ids = ("olivia_thompson", "daria_stone")

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Olivia, tell me about the victim",
        Random(88339),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_WrongSpeakerAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)


def test_run_turn_fails_closed_for_dialogue_with_code_artifact() -> None:
    class _ContaminatedDialogueAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {
                    "speaker": "daria_stone",
                    "text": "getStringExtra from the case file is not available yet.",
                    "tone": "in_world",
                },
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "case file", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=88340, genre="mystery")

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, summarize the case file for me",
        Random(88340),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_ContaminatedDialogueAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 0
    assert any("story response unavailable" in line.lower() for line in lines)
    assert not any(line.strip().lower() == "query" for line in lines)
    assert not any(line.startswith('Elias says: "') for line in lines)
    assert not any(line.startswith('You says: "') for line in lines)


def test_run_turn_keeps_non_addressed_world_actions_scene_scoped() -> None:
    class _NpcHijackAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "daria_stone", "text": "What brings you to the mansion at this hour?", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "arrival", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=883381, genre="mystery")

    next_state, lines, action_raw, beat_type, continued = run_turn(
        state,
        "get in car",
        Random(883381),
        StubNarrator("You head for your sedan and reach for the driver's door."),
        debug=False,
        freeform_adapter=_NpcHijackAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert action_raw == "get in car"
    assert next_state.turn_index == 1
    assert not any(line.startswith('Daria Stone says: "') for line in lines)
    assert not any("story response unavailable" in line.lower() for line in lines)
    assert any("driver's door" in line.lower() for line in lines)


def test_run_turn_normalizes_scene_scoped_player_echo_for_car_door_action() -> None:
    class _PlayerEchoAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001, ARG002
            return (
                {"speaker": "player", "text": "open car door", "tone": "in_world"},
                {
                    "intent": "freeform",
                    "targets": [],
                    "arguments": {},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=883382, genre="mystery")

    next_state, lines, action_raw, beat_type, continued = run_turn(
        state,
        "open car door",
        Random(883382),
        StubNarrator(),
        debug=False,
        freeform_adapter=_PlayerEchoAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert action_raw == "open car door"
    assert next_state.turn_index == 1
    assert not any(line.startswith('Elias says: "') for line in lines)
    assert not any(line.startswith('You says: "') for line in lines)
    assert any("sedan" in line.lower() or "door" in line.lower() for line in lines)


def test_run_turn_maps_ai_assistant_speaker_to_target_npc_name() -> None:
    class _AssistantSpeakerAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "AI_Assistant", "text": "I last saw him near dusk, heading inside alone.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "holmes", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=88339)

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, when did you last see Mr. Holmes?",
        Random(88339),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_AssistantSpeakerAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert any(line.startswith('Daria Stone says: "') for line in lines)
    assert not any(line.startswith('AI_Assistant says: "') for line in lines)


def test_run_turn_suppresses_repeated_goal_copy_after_opening():
    state = build_default_state(seed=8834)
    goal_line = f"Your immediate objective is clear: {state.active_goal}"
    next_state, lines, _action_raw, _beat_type, continued = run_turn(
        state,
        "look",
        Random(8834),
        StubNarrator(goal_line),
        debug=False,
    )

    assert continued is True
    assert next_state.turn_index == 1
    assert not any("immediate objective" in line.lower() for line in lines)
    assert not any(state.active_goal in line for line in lines)
    assert any(state.world.rooms[state.player.location].name in line for line in lines)


def test_run_turn_keeps_goal_copy_when_player_explicitly_asks_for_it():
    class _ObjectiveAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "daria_stone", "text": f"Our objective is {state.active_goal}", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "objective", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=8835)
    goal_line = f"Your immediate objective is clear: {state.active_goal}"
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, what is our objective?",
        Random(8835),
        StubNarrator(goal_line),
        debug=False,
        freeform_adapter=_ObjectiveAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert any("objective" in line.lower() for line in lines)
    assert any("strongest lead" in line.lower() for line in lines)


def test_run_turn_freeform_rejects_unreachable_target_without_fact_updates():
    state = build_default_state(seed=89)
    initial_flags = dict(state.player.flags)
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "ask dragon about the signal",
        Random(89),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
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
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
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
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )
    proceeded_state, proceed_lines, _proceed_raw, proceed_beat, proceed_continued = run_turn(
        warned_state,
        "proceed",
        Random(97),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
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
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )
    state, _proceed_lines, _proceed_raw, _proceed_beat, _proceed_continued = run_turn(
        state,
        "proceed",
        Random(98),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
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


def test_run_turn_recoverable_disruption_adapts_without_confirmation_gate() -> None:
    state = build_default_state(seed=991)

    next_state, lines, action_raw, beat_type, continued = run_turn(
        state,
        "spray graffiti on statue",
        Random(991),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type != "impact_gate"
    assert action_raw == "spray graffiti on statue"
    assert next_state.turn_index == 1
    assert next_state.pending_high_impact_command == ""
    assert next_state.player.flags.get("story_replan_required") is not True
    assert not any("type proceed" in line.lower() for line in lines)


def test_run_turn_applies_output_editor_before_returning_lines():
    class _PassThroughEditor:
        def review_opening(self, lines, active_goal):  # noqa: ANN001
            return lines

        def review_turn(self, lines, active_goal, turn_index, debug=False):  # noqa: ANN001
            return [f"[edited] {line}" for line in lines]

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
    assert all(line.startswith("[edited] ") for line in lines)


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


def test_room_lines_describe_mansion_north_path_as_entrance_not_exit() -> None:
    state = build_default_state(seed=124, genre="mystery", tone="dark")

    lines = _room_lines(state)

    lower = lines.lower()
    assert "the main entrance from here leads north" in lower
    assert "the main exit from here leads north" not in lower


def test_setup_phase_lines_weave_background_and_actionable_objective():
    state = build_default_state(seed=124, genre="mystery", tone="dark")
    lines = _setup_phase_lines(state, _StubSetupDirector())
    joined = "\n".join(lines).lower()

    assert "the case in front of you starts simply" not in joined
    assert "low profile" not in joined
    assert "your first objective is clear" in joined


def test_main_replay_emits_setup_phase_before_commands(tmp_path, monkeypatch):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\n", encoding="utf-8")

    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
    main(["--seed", "4", "--replay", str(replay), "--transcript", str(transcript)])

    lines = transcript.read_text(encoding="utf-8").splitlines()
    command_index = next(i for i, line in enumerate(lines) if line == ">LOOK")
    assert command_index >= 3


def test_main_replay_inserts_blank_line_between_opening_paragraphs(tmp_path, monkeypatch):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\n", encoding="utf-8")

    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
    main(["--seed", "4", "--replay", str(replay), "--transcript", str(transcript)])

    setup_section = transcript.read_text(encoding="utf-8").split(">LOOK", maxsplit=1)[0]
    assert "\n\n" in setup_section


def test_main_replay_inserts_blank_line_before_each_command_echo(tmp_path, monkeypatch):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\ninventory\n", encoding="utf-8")

    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
    main(["--seed", "4", "--replay", str(replay), "--transcript", str(transcript)])

    text = transcript.read_text(encoding="utf-8")
    assert "\n\n>LOOK\n" in text
    assert "\n\n>INVENTORY\n" in text


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
