from __future__ import annotations

from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state


def test_default_state_initializes_core_world_facts() -> None:
    state = build_default_state(seed=5)

    assert state.world_facts.holds("at", "player", "harbor")
    assert state.world_facts.holds("holding", "player", "torch")
    assert state.world_facts.holds("path", "north", "harbor", "market")
    assert state.world_facts.holds("room_item", "market", "bronze_key")


def test_move_and_take_update_facts_and_legacy_views() -> None:
    state = build_default_state(seed=6)

    after_move, move_events = apply_action(state, parse_command("north"), Random(6))
    assert any(event.type == "move" for event in move_events)
    assert after_move.world_facts.holds("at", "player", "market")
    assert after_move.player.location == "market"

    after_take, take_events = apply_action(after_move, parse_command("take bronze key"), Random(6))
    assert any(event.type == "take" for event in take_events)
    assert after_take.world_facts.holds("holding", "player", "bronze_key")
    assert not after_take.world_facts.holds("room_item", "market", "bronze_key")
    assert "bronze_key" in after_take.player.inventory
