"""Generic, fact-backed presentation helpers for runtime projections."""

# ruff: noqa: E501

from __future__ import annotations

from storygame.engine.facts import (
    active_story_goal,
    case_facts,
    discovered_leads,
    hidden_story_threads,
    planned_story_events,
)
from storygame.engine.state import GameState, Item, Npc, Room

ACTIONABLE_ITEM_KINDS = {"tool", "clue", "evidence", "vehicle"}
_NAME_PREFIXES = {"detective", "doctor", "dr", "mr", "mrs", "ms", "professor", "prof", "captain", "officer"}


def _given_name(name: str) -> str:
    parts = name.split()
    if parts and parts[0].rstrip(".").casefold() in _NAME_PREFIXES:
        parts = parts[1:]
    return parts[0] if parts else name


def npc_reference_name(state: GameState, npc: Npc) -> str:
    """Use a full name once, then a unique given name in player-facing prose."""
    introduced = state.world_package.setdefault("introduced_npcs", [])
    if npc.id not in introduced:
        introduced.append(npc.id)
        return npc.name
    given_name = _given_name(npc.name)
    matching_given_names = sum(
        _given_name(candidate.name).casefold() == given_name.casefold() for candidate in state.world.npcs.values()
    )
    return given_name if matching_given_names == 1 else npc.name


def is_actionable_item(item: Item) -> bool:
    return "quest" in item.tags or item.kind in ACTIONABLE_ITEM_KINDS


def room_item_groups(state: GameState, room: Room) -> tuple[tuple[str, ...], int]:
    actionable = tuple(item_id for item_id in room.item_ids if is_actionable_item(state.world.items[item_id]))
    return actionable, len(room.item_ids) - len(actionable)


def room_arrival_lines(state: GameState, room_id: str, first_visit: bool) -> tuple[str, ...]:
    """Render a fact-backed room arrival without replaying the story opening."""
    room = state.world.rooms[room_id]
    lines: list[str] = []
    if first_visit:
        cache = state.world_package.get("room_presentation_cache", {}).get(room_id, {})
        description = str(cache.get("long", room.description)).strip()
        if description:
            lines.append(f"{room.name}: {description}")

    contents = [state.world.npcs[npc_id].name for npc_id in room.npc_ids if npc_id in state.world.npcs]
    contents.extend(state.world.items[item_id].name for item_id in room.item_ids if item_id in state.world.items)
    contents_text = ", ".join(contents) if contents else "nothing notable"
    exits = [
        state.world.rooms[destination].name for destination in room.exits.values() if destination in state.world.rooms
    ]
    exits_text = ", ".join(exits) if exits else "none"
    lines.append(f"Contents: {contents_text}. Exits: {exits_text}.")
    return tuple(lines)


def filtered_inventory(state: GameState) -> tuple[str, ...]:
    return tuple(
        item_id
        for item_id in state.player.inventory
        if (item := state.world.items.get(item_id)) is not None and is_actionable_item(item)
    )


def take_item_message(item: Item) -> str:
    if item.kind == "evidence" and item.clue_text:
        return f"Evidence secured: {item.clue_text}"
    if item.kind == "clue" and item.clue_text:
        return f"Clue noted: {item.clue_text}"
    if item.kind == "tool":
        return f"Tool acquired: {item.name}."
    return "take_success"


def npc_talk_message(_state: GameState, npc: Npc, first_talk: bool) -> str:
    if first_talk:
        return npc.dialogue
    return f"{npc_reference_name(_state, npc)} has nothing new to add right now."


def story_status_lines(state: GameState) -> tuple[str, ...]:
    """Render a generic, fact-backed progress projection for the CLI."""
    known_facts = [
        f"Current objective: {active_story_goal(state)}",
        f"Progress is {state.progress:.2f} with tension {state.tension:.2f}.",
        *(f"{entry['key'].replace('_', ' ').title()}: {entry['value']}" for entry in case_facts(state)),
    ]
    if state.beat_history:
        known_facts.append(f"Latest beat: {state.beat_history[-1]}.")

    leads = [entry["text"] for entry in discovered_leads(state)]
    leads.extend(str(event["summary"]) for event in planned_story_events(state))
    leads.extend(hidden_story_threads(state))
    room = state.world.rooms[state.player.location]
    if not leads and room.item_ids:
        leads.append(f"Inspect available items in {room.name}.")
    if len(leads) < 3 and room.npc_ids:
        leads.append(f"Speak with {room.npc_ids[0].replace('_', ' ')} for new context.")
    if not leads:
        leads.append("Explore adjacent rooms to gather more context.")

    return (
        "Story status:",
        "Known facts: " + " | ".join(known_facts[:3]),
        "Open questions: Which scene should be explored next? | Which available person or item can change the situation?",
        "Active leads: " + " | ".join(leads[:3]),
    )
