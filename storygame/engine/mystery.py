from __future__ import annotations

from storygame.engine.facts import active_story_goal, discovered_leads
from storygame.engine.state import GameState, Item, Npc, Room

ACTIONABLE_ITEM_KINDS = {"tool", "clue", "evidence"}


def is_actionable_item(item: Item) -> bool:
    if "quest" in item.tags:
        return True
    return item.kind in ACTIONABLE_ITEM_KINDS


def room_item_groups(state: GameState, room: Room) -> tuple[tuple[str, ...], int]:
    actionable: list[str] = []
    junk_count = 0
    for item_id in room.item_ids:
        item = state.world.items[item_id]
        if is_actionable_item(item):
            actionable.append(item_id)
        else:
            junk_count += 1
    return tuple(actionable), junk_count


def filtered_inventory(state: GameState) -> tuple[str, ...]:
    inventory: list[str] = []
    for item_id in state.player.inventory:
        item = state.world.items.get(item_id)
        if item is None:
            continue
        if is_actionable_item(item):
            inventory.append(item_id)
    return tuple(inventory)


def take_item_message(item: Item) -> str:
    if item.kind == "evidence" and item.clue_text:
        return f"Evidence secured: {item.clue_text}"
    if item.kind == "clue" and item.clue_text:
        return f"Clue noted: {item.clue_text}"
    if item.kind == "tool":
        return f"Tool acquired: {item.name}."
    return "take_success"


def npc_talk_message(state: GameState, npc: Npc, first_talk: bool) -> str:
    if first_talk:
        return npc.dialogue
    return f"{npc.name} has nothing new to add right now."


def caseboard_lines(state: GameState) -> tuple[str, ...]:
    known_facts = [
        f"Current objective: {active_story_goal(state)}",
        f"Progress is {state.progress:.2f} with tension {state.tension:.2f}.",
    ]
    if state.beat_history:
        known_facts.append(f"Latest beat: {state.beat_history[-1]}.")

    open_questions = [
        "Which scene should be explored next?",
        "Which NPC or item can unlock the next progression step?",
    ]

    leads = [entry["text"] for entry in discovered_leads(state)]
    room = state.world.rooms[state.player.location]
    if not leads and room.item_ids:
        leads.append(f"Inspect available items in {room.name}.")
    if len(leads) < 3 and room.npc_ids:
        leads.append(f"Question {room.npc_ids[0].replace('_', ' ')} for new context.")
    if not leads:
        leads.append("Explore adjacent rooms to gather more context.")

    return (
        "Caseboard:",
        "Known facts: " + " | ".join(known_facts[:3]),
        "Open questions: " + " | ".join(open_questions[:2]),
        "Active leads: " + " | ".join(leads[:3]),
    )
