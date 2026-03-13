from __future__ import annotations

from random import Random

from storygame.cli import _room_lines, run_turn
from storygame.engine.parser import parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state
from storygame.llm.adapters import SilentNarrator
from storygame.llm.context import build_narration_context


def test_room_lines_include_room_identity_and_navigation():
    state = build_default_state(seed=31, genre="fantasy", tone="epic")
    lines = _room_lines(state)
    room = state.world.rooms[state.player.location]

    assert room.name in lines
    assert room.description in lines
    assert "exit" in lines.lower()


def test_starting_state_avoids_meta_room_text_and_starts_with_kit():
    state = build_default_state(seed=35, genre="mystery")
    room = state.world.rooms[state.player.location]

    assert "move the story toward resolution" not in room.description.lower()
    assert "neutral mystery scene" not in room.description.lower()
    assert "field_kit" in state.player.inventory
    assert "field_kit" not in room.item_ids


def test_context_filters_inventory_to_actionable_items():
    state = build_default_state(seed=32, genre="thriller")
    context = build_narration_context(state, parse_command("look"), "hook")
    payload = context.as_dict()

    assert "field_kit" in payload["inventory"]
    assert payload["npc_facts"]


def test_talk_sets_flag_for_present_npc_and_message_is_world_facing():
    state = build_default_state(seed=33, genre="adventure")
    room = state.world.rooms[state.player.location]
    npc_id = room.npc_ids[0]

    next_state, events = apply_action(state, parse_command(f"talk {npc_id}"), Random(33))
    talk_messages = [event.message_key for event in events if event.type == "talk"]

    assert talk_messages
    assert next_state.player.flags.get(f"talked_{npc_id}") is True
    assert isinstance(talk_messages[0], str)
    assert talk_messages[0].strip()


def test_unknown_non_command_routes_to_freeform_roleplay():
    state = build_default_state(seed=34, genre="suspense")
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "ask about the latest clue",
        Random(34),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert lines
