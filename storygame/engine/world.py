from __future__ import annotations

import re

from storygame.engine.facts import initialize_world_facts, sync_legacy_views
from storygame.engine.state import GameState, Item, Npc, PlayerState, Room, WorldState
from storygame.engine.world_builder import build_world_package


def _humanize_identifier(value: str) -> str:
    text = value.replace("_", " ").replace("-", " ").strip()
    return re.sub(r"\s+", " ", text).title()


def _slugify_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    normalized = normalized.strip("_")
    return normalized or "npc"


def _item_kind_for_index(index: int) -> str:
    if index == 0:
        return "tool"
    if index == 1:
        return "clue"
    return "evidence"


def _room_name_for_display(room_id: str, genre: str) -> str:
    if genre == "mystery" and room_id == "front_steps":
        return "Outside The Mansion"
    return _humanize_identifier(room_id)


def _room_description(room_id: str, genre: str, tone: str) -> str:
    location = room_id.replace("_", " ")
    if genre == "mystery" and room_id == "front_steps":
        return (
            "Stone steps lead toward the mansion entrance while the street behind you stays active with distant "
            "voices and restless weather."
        )
    return f"A {tone} {genre} location around {location}, detailed enough to investigate without revealing its secrets at once."


def _build_items(package: dict) -> dict[str, Item]:
    item_ids = tuple(package["item_graph"]["items"])
    primary_goal = str(package["goals"]["primary"])
    items: dict[str, Item] = {}
    for index, item_id in enumerate(item_ids):
        kind = _item_kind_for_index(index)
        items[item_id] = Item(
            id=item_id,
            name=_humanize_identifier(item_id),
            description=f"An important {kind} tied to your current objective.",
            tags=("quest", package["genre"], kind),
            kind=kind,
            delta_progress=0.07 + (0.02 * min(index, 3)),
            clue_text=f"It may help with: {primary_goal}",
        )

    # Always include a baseline utility item for stable command flow.
    items["field_kit"] = Item(
        id="field_kit",
        name="Field Kit",
        description="Basic tools packed before the journey began.",
        tags=("tool",),
        kind="tool",
    )
    return items


def _build_npcs(package: dict) -> dict[str, Npc]:
    npcs: dict[str, Npc] = {}
    for index, npc_name in enumerate(package["entities"]["npcs"]):
        npc_id = _slugify_name(npc_name)
        npcs[npc_id] = Npc(
            id=npc_id,
            name=npc_name,
            description=f"{npc_name} watches the situation carefully.",
            dialogue=f"Stay focused on the objective: {package['goals']['primary']}",
            identity=f"{package['genre']} world participant",
            pronouns="they/them",
            tags=(package["genre"],),
            delta_progress=0.05 if index < 3 else 0.0,
            knowledge_source="witness account",
        )
    return npcs


def _build_room_exits(paths: tuple[dict, ...] | list[dict]) -> dict[str, dict[str, str]]:
    exits: dict[str, dict[str, str]] = {}
    for path in paths:
        exits.setdefault(path["from"], {})[path["direction"]] = path["to"]
    return exits


def _build_rooms(package: dict, items: dict[str, Item], npcs: dict[str, Npc]) -> dict[str, Room]:
    room_ids = tuple(package["map"]["rooms"])
    exits = _build_room_exits(tuple(package["map"]["paths"]))
    item_ids = tuple(item_id for item_id in items if item_id != "field_kit")
    npc_ids = tuple(npcs.keys())

    rooms: dict[str, Room] = {}
    for index, room_id in enumerate(room_ids):
        assigned_items: list[str] = []
        if index < len(item_ids):
            assigned_items.append(item_ids[index])

        assigned_npcs: list[str] = []
        if index < len(npc_ids):
            assigned_npcs.append(npc_ids[index])

        rooms[room_id] = Room(
            id=room_id,
            name=_room_name_for_display(room_id, package["genre"]),
            description=_room_description(room_id, package["genre"], package["tone"]),
            exits=dict(exits.get(room_id, {})),
            item_ids=tuple(assigned_items),
            npc_ids=tuple(assigned_npcs),
        )

    # Ensure the first room is playable even when package data is sparse.
    if room_ids:
        first_room = rooms[room_ids[0]]
        if not first_room.item_ids:
            first_room.item_ids = ("field_kit",)
        elif "field_kit" not in first_room.item_ids:
            first_room.item_ids = ("field_kit", *first_room.item_ids)

    # Add one deterministic lock gate when possible.
    if len(room_ids) >= 3 and item_ids:
        gate_room_id = room_ids[1]
        gate_room = rooms[gate_room_id]
        key_id = item_ids[0]
        if gate_room.exits:
            first_direction = sorted(gate_room.exits.keys())[0]
            gate_room.locked_exits = {first_direction: key_id}

    return rooms


def build_default_state(
    seed: int,
    genre: str = "mystery",
    session_length: int | str = "medium",
    tone: str = "neutral",
) -> GameState:
    package = build_world_package(
        genre=genre,
        session_length=session_length,
        seed=seed,
        tone=tone,
    )

    items = _build_items(package)
    npcs = _build_npcs(package)
    rooms = _build_rooms(package, items, npcs)

    start_room = package["map"]["rooms"][0]
    opening_inventory: list[str] = ["field_kit"]
    if package["genre"] == "mystery" and "case_file" in items:
        opening_inventory.append("case_file")

    start_room_state = rooms[start_room]
    start_room_state.item_ids = tuple(
        item_id for item_id in start_room_state.item_ids if item_id not in opening_inventory
    )
    if not start_room_state.item_ids:
        replacement_item = ""
        replacement_room = ""
        for room_id, room_state in rooms.items():
            for item_id in room_state.item_ids:
                if item_id not in opening_inventory:
                    replacement_item = item_id
                    replacement_room = room_id
                    break
            if replacement_item:
                break
        if replacement_item:
            start_room_state.item_ids = (replacement_item,)
            if replacement_room and replacement_room != start_room:
                source_room = rooms[replacement_room]
                source_room.item_ids = tuple(item_id for item_id in source_room.item_ids if item_id != replacement_item)

    player = PlayerState(
        location=start_room, inventory=tuple(dict.fromkeys(opening_inventory)), flags={"started": True}
    )
    world = WorldState(rooms=rooms, items=items, npcs=npcs)

    state = GameState(
        seed=seed,
        player=player,
        world=world,
        story_genre=package["genre"],
        story_tone=package["tone"],
        session_length=package["session_length"],
        plot_curve_id=package["curve_id"],
        story_outline_id=package["outline"]["id"],
        world_package=package,
        active_goal=str(package["goals"].get("setup", package["goals"]["primary"])),
    )
    initialize_world_facts(state)
    sync_legacy_views(state)
    return state


def build_tiny_state(seed: int) -> GameState:
    # Tiny state now reuses the same world-generation pipeline with a short profile.
    return build_default_state(seed=seed, genre="mystery", session_length="short", tone="neutral")
