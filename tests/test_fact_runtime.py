from __future__ import annotations

from random import Random

from storygame.engine.facts import apply_fact_ops
from storygame.engine.parser import parse_command
from storygame.engine.rules import apply_action
from storygame.engine.state import Npc
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


def test_taking_clue_or_evidence_asserts_discovered_lead_facts() -> None:
    state = build_default_state(seed=7, genre="mystery")
    start_room = state.world.rooms[state.player.location]
    target_item_id = next(
        item_id
        for item_id in (*start_room.item_ids, *(fact[2] for fact in state.world_facts.query("holding", "daria_stone", None)))
        if state.world.items[item_id].kind in {"clue", "evidence"} and state.world.items[item_id].clue_text
    )

    next_state, _events = apply_action(state, parse_command(f"take {target_item_id}"), Random(7))

    assert next_state.world_facts.holds("discovered_clue", target_item_id)
    discovered_leads = next_state.world_facts.query("discovered_lead", target_item_id, None)
    assert discovered_leads


def test_assistant_follows_player_move_via_fact_store_updates() -> None:
    state = build_default_state(seed=21, genre="mystery")
    start_room = state.player.location
    assistant_id = state.world.rooms[start_room].npc_ids[0]
    direction, destination = next(iter(state.world.rooms[start_room].exits.items()))

    next_state, events = apply_action(state, parse_command(direction), Random(21))

    assert any(event.type == "move" for event in events)
    assert next_state.world_facts.holds("npc_at", assistant_id, destination)
    assert assistant_id in next_state.world.rooms[destination].npc_ids
    assert assistant_id not in next_state.world.rooms[start_room].npc_ids


def test_assistant_can_be_marked_absent_and_stop_following() -> None:
    state = build_default_state(seed=22, genre="mystery")
    start_room = state.player.location
    assistant_id = state.world.rooms[start_room].npc_ids[0]
    direction, destination = next(iter(state.world.rooms[start_room].exits.items()))
    apply_fact_ops(state, [{"op": "assert", "fact": ("npc_absent", assistant_id)}])

    next_state, _events = apply_action(state, parse_command(direction), Random(22))

    assert next_state.world_facts.holds("npc_at", assistant_id, start_room)
    assert not next_state.world_facts.holds("npc_at", assistant_id, destination)


def test_generic_npc_location_assert_updates_fact_store_and_legacy_views() -> None:
    state = build_default_state(seed=23, genre="mystery")
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    destination = next(room_id for room_id in state.world.rooms if room_id != state.player.location)

    apply_fact_ops(state, [{"op": "assert", "fact": ("npc_at", npc_id, destination)}])

    npc_locations = state.world_facts.query("npc_at", npc_id, None)
    assert npc_locations == (("npc_at", npc_id, destination),)
    assert npc_id in state.world.rooms[destination].npc_ids


def test_holding_assert_retracts_room_item_and_previous_holder() -> None:
    state = build_default_state(seed=24, genre="mystery")
    room_id = state.player.location
    state.world.rooms[room_id].npc_ids = state.world.rooms[room_id].npc_ids + ("alex_hale",)
    state.world.npcs["alex_hale"] = Npc(
        id="alex_hale",
        name="Alex Hale",
        description="Alex watches the doorway.",
        dialogue="Noted.",
        identity="witness",
        pronouns="he/him",
    )
    state.world_facts.assert_fact("npc_at", "alex_hale", room_id)
    state.world_facts.assert_fact("holding", "player", "ledger_page")

    apply_fact_ops(state, [{"op": "assert", "fact": ("holding", "alex_hale", "ledger_page")}])

    assert state.world_facts.holds("holding", "alex_hale", "ledger_page")
    assert not state.world_facts.holds("holding", "player", "ledger_page")
    assert not state.world_facts.holds("room_item", room_id, "ledger_page")
