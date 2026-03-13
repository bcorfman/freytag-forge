from __future__ import annotations

from storygame.engine.mystery import caseboard_lines, filtered_inventory, take_item_message
from storygame.engine.state import Item
from storygame.engine.world import build_default_state


def test_filtered_inventory_skips_missing_items_and_non_actionable_items() -> None:
    state = build_default_state(seed=611)
    state.player.inventory = ("missing_item", "field_kit")
    filtered = filtered_inventory(state)
    assert "missing_item" not in filtered


def test_take_item_message_branches_for_item_kinds() -> None:
    state = build_default_state(seed=612)
    evidence = next(item for item in state.world.items.values() if item.kind == "evidence")
    clue = next(item for item in state.world.items.values() if item.kind == "clue")
    tool = next(item for item in state.world.items.values() if item.kind == "tool")
    junk = Item(id="junk_x", name="Scrap", description="unused", kind="junk")

    assert take_item_message(evidence).startswith("Evidence secured:")
    assert take_item_message(clue).startswith("Clue noted:")
    assert take_item_message(tool).startswith("Tool acquired:")
    assert take_item_message(junk) == "take_success"


def test_caseboard_lines_fallback_lead_when_no_items_or_npcs() -> None:
    state = build_default_state(seed=613)
    room = state.world.rooms[state.player.location]
    room.item_ids = ()
    room.npc_ids = ()
    state.beat_history = ()

    lines = caseboard_lines(state)
    joined = "\n".join(lines).lower()
    assert "explore adjacent rooms" in joined
    assert "latest beat" not in joined
