from __future__ import annotations

from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state


def test_default_state_initializes_core_world_facts() -> None:
    state = build_default_state(seed=5, genre="fantasy")
    rooms = state.world_package["map"]["rooms"]
    start_room = rooms[0]
    first_path = state.world_package["map"]["paths"][0]
    locked_facts = state.world_facts.query("locked", None, None, None)

    assert state.world_facts.holds("at", "player", start_room)
    assert state.world_facts.holds(
        "path",
        first_path["direction"],
        first_path["from"],
        first_path["to"],
    )
    assert locked_facts


def test_move_and_take_update_facts_and_legacy_views() -> None:
    state = build_default_state(seed=6, genre="thriller")
    first_room = state.world.rooms[state.player.location]
    direction, destination = next(iter(first_room.exits.items()))
    destination_items = tuple(state.world.rooms[destination].item_ids)
    assert destination_items

    after_move, move_events = apply_action(state, parse_command(direction), Random(6))
    assert any(event.type == "move" for event in move_events)
    assert after_move.world_facts.holds("at", "player", destination)
    assert after_move.player.location == destination

    item_id = destination_items[0]
    after_take, take_events = apply_action(after_move, parse_command(f"take {item_id}"), Random(6))
    assert any(event.type == "take" for event in take_events)
    assert after_take.world_facts.holds("holding", "player", item_id)
    assert not after_take.world_facts.holds("room_item", destination, item_id)
    assert item_id in after_take.player.inventory
