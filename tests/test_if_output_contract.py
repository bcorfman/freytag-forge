from __future__ import annotations

import json
from random import Random

from storygame.cli import main, run_turn
from storygame.engine.freeform import RuleBasedFreeformProposalAdapter
from storygame.engine.world import build_default_state
from storygame.llm.adapters import SilentNarrator
from tests.narrator_stubs import StubNarrator


def _run_script(seed: int, commands: list[str]) -> tuple[list[list[str]], list[str]]:
    state = build_default_state(seed)
    rng = Random(seed)
    per_turn_lines: list[list[str]] = []
    signatures: list[str] = []
    for command in commands:
        state, lines, _action_raw, _beat, continued = run_turn(state, command, rng, StubNarrator(), debug=False)
        per_turn_lines.append(lines)
        signatures.append(state.replay_signature())
        if not continued:
            break
    return per_turn_lines, signatures


class _StubSetupDirector:
    def compose_opening(self, state):  # noqa: ANN001
        return list(state.world_package.get("story_plan", {}).get("setup_paragraphs", ()))

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001
        return lines


def test_non_debug_output_is_room_first_and_hides_internal_labels():
    state = build_default_state(seed=31)
    room = state.world.rooms[state.player.location]
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(31),
        SilentNarrator(),
        debug=False,
    )

    assert lines
    assert lines[0].startswith(f"{room.name}\n")
    assert room.description in lines[0]
    assert all("[debug]" not in line for line in lines)
    assert all("judge_status=" not in line for line in lines)
    assert all("coherence_budget" not in line for line in lines)
    assert all(not line.startswith("- ") for line in lines)
    assert all(" beat at " not in line.lower() for line in lines)


def test_turn_output_prefers_llm_narration_block_over_deterministic_room_block():
    state = build_default_state(seed=311)
    room = state.world.rooms[state.player.location]
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(311),
        StubNarrator("You scan the courtyard, cataloging items, exits, and every flicker of movement."),
        debug=False,
    )

    assert len(lines) == 1
    assert lines[0].startswith(f"{room.name}\n")
    assert room.description not in lines[0]


def test_per_turn_room_block_follows_expected_section_order():
    state = build_default_state(seed=133)
    room = state.world.rooms[state.player.location]
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(133),
        SilentNarrator(),
        debug=False,
    )

    room_block = lines[0].splitlines()
    assert room_block[0] == room.name
    assert room.description in room_block[1]

    item_index = next(i for i, line in enumerate(room_block) if "you can see" in line.lower())
    exit_index = next(i for i, line in enumerate(room_block) if "exit" in line.lower())
    assert item_index < exit_index

    npc_line_indices = [
        i for i, line in enumerate(room_block) if " is here." in line.lower() or " are here." in line.lower()
    ]
    if npc_line_indices:
        assert npc_line_indices[0] > exit_index

    assert len(lines) >= 2
    assert lines[1].strip()


def test_unknown_non_command_input_uses_in_world_roleplay_response():
    state = build_default_state(seed=32)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        f"ask {npc_id} about rumors",
        Random(32),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert any("story response unavailable" in line.lower() for line in lines)


def test_debug_mode_emits_parseable_internal_trace():
    state = build_default_state(seed=33)
    _next_state, lines, _action_raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(33),
        StubNarrator(),
        debug=True,
    )

    debug_json_lines = [line for line in lines if line.startswith("[debug-json] ")]
    assert debug_json_lines
    payload = json.loads(debug_json_lines[-1].replace("[debug-json] ", "", 1))
    assert payload["judge"]["decision_id"]
    assert payload["coherence"]["critique_rounds"] >= 0


def test_transcript_uses_prompt_echo_format(tmp_path, monkeypatch):
    replay = tmp_path / "commands.txt"
    transcript = tmp_path / "transcript.txt"
    replay.write_text("look\ninventory\n", encoding="utf-8")

    monkeypatch.setattr("storygame.cli.StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005
    main(["--seed", "123", "--replay", str(replay), "--transcript", str(transcript)])

    text = transcript.read_text(encoding="utf-8")
    assert ">LOOK" in text
    assert ">INVENTORY" in text
    assert "CMD " not in text
    assert "Before dawn" not in text


def test_fixed_seed_replay_is_byte_stable_for_output_and_state():
    commands = ["look", "north", "look", "inventory", "look"]
    first_output, first_state = _run_script(77, commands)
    second_output, second_state = _run_script(77, commands)

    assert first_output == second_output
    assert first_state == second_state
