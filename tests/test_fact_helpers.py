from __future__ import annotations

from storygame.engine.facts import (
    beat_phase,
    beat_role,
    current_scene,
    dramatic_question,
    npc_stance_toward_player,
    npc_trust_toward_player,
    player_approach,
    replace_player_flags,
    replace_player_inventory,
    replace_room_items,
    scene_location,
    scene_objective,
    scene_participants,
    scene_pressure,
    set_player_flag,
    set_player_location,
)
from storygame.engine.scene_state import refresh_scene_state
from storygame.engine.world import build_default_state


def test_player_fact_helpers_replace_canonical_location_inventory_and_flags() -> None:
    state = build_default_state(seed=51, genre="mystery")
    destination = next(room_id for room_id in state.world.rooms if room_id != state.player.location)
    item_ids = tuple(item_id for item_id in state.world.items if item_id != "field_kit")[:2]

    set_player_location(state, destination)
    replace_player_inventory(state, item_ids)
    set_player_flag(state, "fact_helper_flag", True)
    set_player_flag(state, "started", False)
    replace_player_flags(state, {"fact_helper_flag": True, "replacement_flag": True})

    assert state.player.location == destination
    assert state.player.inventory == item_ids
    assert state.player.flags["fact_helper_flag"] is True
    assert state.player.flags["replacement_flag"] is True
    assert state.player.flags["started"] is False
    assert state.world_facts.holds("at", "player", destination)
    assert state.world_facts.holds("holding", "player", item_ids[0])
    assert not state.world_facts.holds("flag", "player", "started")


def test_replace_room_items_updates_room_projection_from_fact_store() -> None:
    state = build_default_state(seed=52, genre="mystery")
    room_id = state.player.location
    replacement_items = tuple(item_id for item_id in state.world.items if item_id not in state.player.inventory)[:2]

    replace_room_items(state, room_id, replacement_items)

    assert state.world.rooms[room_id].item_ids == replacement_items
    assert state.world_facts.query("room_item", room_id, None) == tuple(
        ("room_item", room_id, item_id) for item_id in replacement_items
    )


def test_scene_fact_helpers_read_back_refresh_scene_state_outputs() -> None:
    state = build_default_state(seed=53, genre="mystery")
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    refresh_scene_state(
        state,
        {
            "player_approach": "question",
            "dramatic_question": "Will Daria Stone answer questions about the ledger page?",
            "beat_role": "reveal",
            "scene_pressure": "pressured",
            "beat_phase": "rising_action",
        },
    )
    state.world_facts.assert_fact("npc_stance", npc_id, "player", "guarded")
    state.world_facts.assert_fact("npc_trust", npc_id, "player", "wary")

    scene_id = current_scene(state)

    assert scene_location(state, scene_id) == state.player.location
    assert scene_objective(state, scene_id) == state.active_goal
    assert dramatic_question(state, scene_id) == "Will Daria Stone answer questions about the ledger page?"
    assert scene_pressure(state, scene_id) == "pressured"
    assert beat_phase(state) == "rising_action"
    assert beat_role(state, scene_id) == "reveal"
    assert player_approach(state) == "question"
    assert "player" in scene_participants(state, scene_id)
    assert npc_stance_toward_player(state, npc_id) == "guarded"
    assert npc_trust_toward_player(state, npc_id) == "wary"


def test_scene_fact_helpers_fall_back_when_scene_facts_are_absent() -> None:
    state = build_default_state(seed=54, genre="thriller")
    state.world_facts.replace_all(
        tuple(fact for fact in state.world_facts.all() if fact[0] not in {"current_scene", "scene_location", "scene_objective", "dramatic_question", "scene_pressure", "beat_phase", "beat_role", "player_approach", "scene_participant"})
    )

    fallback_scene_id = f"scene:{state.player.location}"

    assert current_scene(state) == fallback_scene_id
    assert scene_location(state, fallback_scene_id) == state.player.location
    assert scene_objective(state, fallback_scene_id) == state.active_goal
    assert dramatic_question(state, fallback_scene_id) == ""
    assert scene_pressure(state, fallback_scene_id) == ""
    assert beat_phase(state) == ""
    assert beat_role(state, fallback_scene_id) == ""
    assert player_approach(state) == ""
    assert scene_participants(state, fallback_scene_id) == ()
