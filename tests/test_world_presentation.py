from __future__ import annotations

from random import Random

from storygame.cli import _room_lines, run_turn
from storygame.engine.facts import protagonist_profile
from storygame.engine.freeform import RuleBasedFreeformProposalAdapter
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


def test_mystery_starting_state_seeds_canonical_protagonist_name_fact():
    state = build_default_state(seed=351, genre="mystery")

    assert protagonist_profile(state)["name"] == "Detective Elias Wren"
    assert state.world_facts.holds("player_name", "Detective Elias Wren")


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
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert lines


def test_room_presentation_uses_short_on_move_and_long_on_look():
    state = build_default_state(seed=36, genre="mystery")
    direction = sorted(state.world.rooms[state.player.location].exits.keys())[0]
    destination = state.world.rooms[state.player.location].exits[direction]

    moved_state, move_lines, _action_raw, _beat_type, _continued = run_turn(
        state,
        direction,
        Random(36),
        SilentNarrator(),
        debug=False,
    )
    cache = moved_state.world_package["room_presentation_cache"][destination]
    assert cache["short"] in move_lines[0]
    assert cache["long"] not in move_lines[0]

    looked_state, look_lines, _action_raw, _beat_type, _continued = run_turn(
        moved_state,
        "look around",
        Random(37),
        SilentNarrator(),
        debug=False,
    )
    look_cache = looked_state.world_package["room_presentation_cache"][destination]
    assert look_cache["long"] in look_lines[0]


def test_same_room_followup_turn_does_not_repeat_room_block():
    state = build_default_state(seed=37, genre="mystery")

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "take the ledger page",
        Random(37),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert beat_type != "setup_scene"
    room = next_state.world.rooms[next_state.player.location]
    assert not any(line.startswith(room.name + "\n") for line in lines)
    assert not any(room.description in line for line in lines)
    assert any("clue noted:" in line.lower() for line in lines)


def test_same_room_freeform_reply_does_not_repeat_room_block():
    state = build_default_state(seed=38, genre="mystery")

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, what are you wearing?",
        Random(38),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    room = next_state.world.rooms[next_state.player.location]
    assert next_state.turn_index == 0
    assert not any(line.startswith(room.name + "\n") for line in lines)
    assert not any(room.description in line for line in lines)
    assert any("story response unavailable" in line.lower() for line in lines)
    assert not any(line.startswith("Daria Stone says:") for line in lines)


def test_take_allows_unique_partial_item_reference_in_room():
    state = build_default_state(seed=39, genre="mystery")
    room = state.world.rooms[state.player.location]
    room.item_ids = ("route_key",)

    next_state, lines, _action_raw, _beat_type, continued = run_turn(
        state,
        "take key",
        Random(39),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert "route_key" in next_state.player.inventory
    assert any("route key" in line.lower() for line in lines)
