from __future__ import annotations

from random import Random

from storygame.engine.parser import Action, ActionKind, parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state


def _reachable_direction_and_destination(state):
    room = state.world.rooms[state.player.location]
    direction, destination = next(iter(room.exits.items()))
    return direction, destination


def _state_with_inventory_item(seed: int):
    state = build_default_state(seed=seed, genre="sci-fi")
    item_id = next(iter(state.world.items.keys()))
    state.player.inventory = (item_id,)
    state.world_facts.assert_fact("holding", "player", item_id)
    return state, item_id


def test_move_by_direction_and_room_name_both_work():
    state = build_default_state(seed=1, genre="adventure")
    direction, destination = _reachable_direction_and_destination(state)

    moved_by_dir, events_dir = apply_action(state, parse_command(direction), Random(1))
    assert moved_by_dir.player.location == destination
    assert any(event.type == "move" for event in events_dir)

    reset_state = build_default_state(seed=1, genre="adventure")
    moved_by_room, events_room = apply_action(reset_state, Action(ActionKind.MOVE, target=destination), Random(1))
    assert moved_by_room.player.location == destination
    assert any(event.type == "move" for event in events_room)


def test_locked_exit_requires_key_then_allows_move():
    state = build_default_state(seed=2, genre="thriller")
    lock_facts = state.world_facts.query("locked", None, None, None)
    assert lock_facts
    direction, room_id, key_id = lock_facts[0][1], lock_facts[0][2], lock_facts[0][3]
    assert room_id in state.world.rooms

    previous_room = state.player.location
    state.player.location = room_id
    state.world_facts.retract_fact("at", "player", previous_room)
    state.world_facts.assert_fact("at", "player", room_id)

    locked_state, locked_events = apply_action(state, parse_command(direction), Random(2))
    assert locked_state.player.location == room_id
    assert any(event.type == "move_failed" for event in locked_events)

    state.player.inventory = (key_id,)
    state.world_facts.assert_fact("holding", "player", key_id)
    unlocked_state, unlocked_events = apply_action(state, parse_command(direction), Random(2))
    assert any(event.type == "move" for event in unlocked_events)
    assert unlocked_state.player.location != room_id


def test_take_and_talk_paths_are_generic():
    state = build_default_state(seed=3, genre="fantasy")
    room = state.world.rooms[state.player.location]
    item_id = room.item_ids[0]
    npc_id = room.npc_ids[0]

    after_take, take_events = apply_action(state, parse_command(f"take {item_id}"), Random(3))
    assert any(event.type == "take" for event in take_events)
    assert item_id in after_take.player.inventory

    after_talk, first_talk_events = apply_action(after_take, parse_command(f"talk {npc_id}"), Random(3))
    _, second_talk_events = apply_action(after_talk, parse_command(f"talk {npc_id}"), Random(3))
    assert any(event.type == "talk" for event in first_talk_events)
    assert any(event.type == "talk" for event in second_talk_events)
    assert any(event.delta_progress == 0.0 for event in second_talk_events)


def test_use_requires_inventory_then_falls_back_to_success():
    missing_state = build_default_state(seed=4, genre="drama")
    missing_item = next(iter(missing_state.world.items.keys()))
    _, missing_events = apply_action(missing_state, parse_command(f"use {missing_item} on target"), Random(4))
    assert any(event.type == "use_failed" for event in missing_events)

    equipped_state, item_id = _state_with_inventory_item(seed=5)
    _, use_events = apply_action(equipped_state, Action(ActionKind.USE, target=f"{item_id}:target"), Random(5))
    assert any(event.type == "use" for event in use_events)
    assert any(event.message_key == "use_success" for event in use_events)
