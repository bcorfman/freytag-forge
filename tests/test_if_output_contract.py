from __future__ import annotations

import json
from random import Random

from storygame.cli import main, run_turn
from storygame.engine.world import build_default_state
from storygame.llm.adapters import MockNarrator, SilentNarrator


def _run_script(seed: int, commands: list[str]) -> tuple[list[list[str]], list[str]]:
    state = build_default_state(seed)
    rng = Random(seed)
    per_turn_lines: list[list[str]] = []
    signatures: list[str] = []
    for command in commands:
        state, lines, _action_raw, _beat, continued = run_turn(state, command, rng, MockNarrator(), debug=False)
        per_turn_lines.append(lines)
        signatures.append(state.replay_signature())
        if not continued:
            break
    return per_turn_lines, signatures


def test_non_debug_output_is_room_first_and_hides_internal_labels():
    state = build_default_state(seed=31)
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(31),
        SilentNarrator(),
        debug=False,
    )

    assert lines
    assert lines[0].startswith("Harbor Steps\n")
    assert "Wind whistles" in lines[0]
    assert all("[debug]" not in line for line in lines)
    assert all("judge_status=" not in line for line in lines)
    assert all("coherence_budget" not in line for line in lines)
    assert all(not line.startswith("- ") for line in lines)
    assert all(" beat at " not in line.lower() for line in lines)


def test_unknown_non_command_input_uses_in_world_roleplay_response():
    state = build_default_state(seed=32)
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "ask ferryman about rumors",
        Random(32),
        SilentNarrator(),
        debug=False,
    )

    assert any("ferryman" in line.lower() for line in lines)
    assert not any("didn't understand" in line.lower() for line in lines)


def test_debug_mode_emits_parseable_internal_trace():
    state = build_default_state(seed=33)
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(33),
        MockNarrator(),
        debug=True,
    )

    debug_json_lines = [line for line in lines if line.startswith("[debug-json] ")]
    assert debug_json_lines
    payload = json.loads(debug_json_lines[-1].replace("[debug-json] ", "", 1))
    assert payload["judge"]["decision_id"]
    assert payload["coherence"]["critique_rounds"] >= 0


def test_transcript_uses_prompt_echo_format(tmp_path):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\ninventory\n", encoding="utf-8")

    main(["--seed", "123", "--replay", str(replay), "--transcript", str(transcript)])

    text = transcript.read_text(encoding="utf-8")
    assert ">LOOK" in text
    assert ">INVENTORY" in text
    assert "CMD " not in text
    assert "Before dawn" not in text


def test_fixed_seed_replay_is_byte_stable_for_output_and_state():
    commands = ["look", "north", "talk keeper", "inventory", "look"]
    first_output, first_state = _run_script(77, commands)
    second_output, second_state = _run_script(77, commands)

    assert first_output == second_output
    assert first_state == second_state
