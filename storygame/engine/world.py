from __future__ import annotations

import re

from storygame.engine.bootstrap import validate_bootstrap_plan
from storygame.engine.facts import (
    initialize_world_facts,
    replace_fact_group,
    set_active_story_goal,
    sync_legacy_views,
)
from storygame.engine.state import GameState, Item, Npc, PlayerState, Room, WorldState
from storygame.engine.world_builder import build_world_package


def _humanize_identifier(value: str) -> str:
    text = value.replace("_", " ").replace("-", " ").strip()
    return re.sub(r"\s+", " ", text).title()


def _slugify_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    normalized = normalized.strip("_")
    return normalized or "npc"


_LIKELY_FEMALE_FIRST_NAMES = {
    "daria",
    "maria",
    "anna",
    "elena",
    "sophia",
    "emily",
    "ava",
    "mia",
    "grace",
    "lily",
    "alice",
    "rachel",
    "julia",
    "sarah",
    "olivia",
    "isabella",
    "amelia",
    "victoria",
    "natasha",
    "anya",
    "leah",
    "nora",
    "zoe",
    "clara",
    "eva",
}

_LIKELY_MALE_FIRST_NAMES = {
    "alexander",
    "noah",
    "liam",
    "ethan",
    "jack",
    "james",
    "daniel",
    "david",
    "michael",
    "john",
    "thomas",
    "henry",
    "ryan",
    "isaac",
    "lucas",
    "nathan",
    "andrew",
    "aaron",
    "max",
    "oliver",
    "samuel",
    "george",
    "arthur",
    "victor",
    "joseph",
}


def _infer_binary_pronouns(name: str) -> str:
    cleaned = " ".join(name.split()).strip().lower()
    first = re.sub(r"[^a-z]", "", cleaned.split(" ")[0]) if cleaned else ""
    if first in _LIKELY_FEMALE_FIRST_NAMES:
        return "she/her"
    if first in _LIKELY_MALE_FIRST_NAMES:
        return "he/him"

    likely_female_suffixes = ("a", "ia", "na", "la", "ra", "elle", "ette", "ina", "aya", "lynn")
    if first.endswith(likely_female_suffixes):
        return "she/her"
    return "he/him"


def _item_kind_for_index(index: int) -> str:
    if index == 0:
        return "tool"
    if index == 1:
        return "clue"
    return "evidence"


def _item_clue_text(item_id: str, genre: str, primary_goal: str) -> str:
    if genre == "mystery":
        if item_id == "case_file":
            return "The case file pins down the victim timeline and highlights the first credible lead."
        if item_id == "ledger_page":
            return "The ledger page records a missing payment tied to the mansion and tonight's visit."
        if item_id == "route_key":
            return "The route key marks a service passage someone expected to use after dark."

    cleaned_goal = primary_goal.strip().rstrip(".")
    if not cleaned_goal:
        return "A concrete lead tied to your current objective."
    return f"A concrete lead tied to your current objective: {cleaned_goal}."


def _room_name_for_display(room_id: str, genre: str) -> str:
    if genre == "mystery" and room_id == "front_steps":
        return "Outside The Mansion"
    if genre == "mystery" and room_id == "foyer":
        return "Mansion Foyer"
    return _humanize_identifier(room_id)


def _room_description(room_id: str, genre: str, tone: str) -> str:
    location = room_id.replace("_", " ")
    if genre == "mystery" and room_id == "front_steps":
        return (
            "Broad stone steps rise to a carved oak door framed by weathered columns. "
            "A brass lantern burns beside the entrance and fresh mud marks the path from the street."
        )
    if genre == "mystery" and room_id == "foyer":
        return (
            "The foyer opens beneath a dim chandelier, with rainwater drying on black-and-white tiles and a long "
            "hall stretching deeper into the mansion."
        )
    return (
        f"The {location} is laid out for close inspection, with worn surfaces and practical routes that can be "
        f"searched room by room in this {tone} {genre} case."
    )


def _build_items(package: dict) -> dict[str, Item]:
    item_ids = tuple(package["item_graph"]["items"])
    primary_goal = str(package["goals"]["primary"])
    genre = str(package["genre"])
    items: dict[str, Item] = {}
    for index, item_id in enumerate(item_ids):
        kind = _item_kind_for_index(index)
        items[item_id] = Item(
            id=item_id,
            name=_humanize_identifier(item_id),
            description=f"An important {kind} tied to your current objective.",
            tags=("quest", genre, kind),
            kind=kind,
            delta_progress=0.07 + (0.02 * min(index, 3)),
            clue_text=_item_clue_text(item_id, genre, primary_goal),
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
            pronouns=_infer_binary_pronouns(npc_name),
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


def _remove_room_item(rooms: dict[str, Room], item_id: str) -> None:
    for room in rooms.values():
        if item_id in room.item_ids:
            room.item_ids = tuple(value for value in room.item_ids if value != item_id)


def _seed_default_mystery_opening(rooms: dict[str, Room]) -> dict[str, str]:
    seeded_holding: dict[str, str] = {}
    _remove_room_item(rooms, "case_file")
    _remove_room_item(rooms, "ledger_page")
    if "daria_stone" in {npc_id for room in rooms.values() for npc_id in room.npc_ids}:
        seeded_holding["ledger_page"] = "daria_stone"
    return seeded_holding


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
    seeded_holding: dict[str, str] = {}
    if package["genre"] == "mystery":
        seeded_holding = _seed_default_mystery_opening(rooms)

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
    if package["genre"] == "mystery":
        start_room_npcs = state.world.rooms[start_room].npc_ids
        if start_room_npcs:
            assistant_id = start_room_npcs[0]
            assistant = state.world.npcs.get(assistant_id)
            if assistant is not None and assistant.name.strip():
                state.world_facts.assert_fact("assistant_name", assistant.name.strip())
                state.world_facts.assert_fact("npc_role", assistant.name.strip(), "assistant")
                state.world_facts.assert_fact("npc_relationship", assistant.name.strip(), "player", "assistant")
        for item_id, holder_id in seeded_holding.items():
            if item_id in state.world.items and holder_id in state.world.npcs:
                state.world_facts.assert_fact("holding", holder_id, item_id)
    sync_legacy_views(state)
    return state


def build_tiny_state(seed: int) -> GameState:
    # Tiny state now reuses the same world-generation pipeline with a short profile.
    return build_default_state(seed=seed, genre="mystery", session_length="short", tone="neutral")


def build_state_from_bootstrap_plan(
    seed: int,
    plan: dict[str, object],
    tone: str = "neutral",
    session_length: str = "medium",
) -> GameState:
    validate_bootstrap_plan(plan)

    plan_locations = tuple(plan["locations"])
    plan_characters = tuple(plan["characters"])
    plan_items = tuple(plan["items"])
    protagonist_id = str(plan["protagonist_id"])
    protagonist = next(character for character in plan_characters if character["id"] == protagonist_id)

    items: dict[str, Item] = {}
    for spec in plan_items:
        items[str(spec["id"])] = Item(
            id=str(spec["id"]),
            name=str(spec["name"]),
            description=str(spec["description"]),
            portable=bool(spec["portable"]),
            tags=tuple(str(trait) for trait in spec["stable_traits"]),
            kind=str(spec["kind"]),
        )

    npcs: dict[str, Npc] = {}
    for spec in plan_characters:
        if spec["id"] == protagonist_id:
            continue
        pronouns = "he/him" if "male" in spec["stable_traits"] else "they/them"
        npcs[str(spec["id"])] = Npc(
            id=str(spec["id"]),
            name=str(spec["name"]),
            description=str(spec["description"]),
            dialogue=f"{spec['name']} weighs the situation before replying.",
            identity=str(spec["role"]),
            pronouns=pronouns,
            tags=tuple(str(trait) for trait in spec["stable_traits"]),
        )

    items_by_room: dict[str, list[str]] = {str(location["id"]): [] for location in plan_locations}
    npc_ids_by_room: dict[str, list[str]] = {str(location["id"]): [] for location in plan_locations}
    for spec in plan_characters:
        if spec["id"] == protagonist_id:
            continue
        npc_ids_by_room[str(spec["location_id"])].append(str(spec["id"]))
    for spec in plan_items:
        location_id = str(spec["location_id"])
        if location_id:
            items_by_room[location_id].append(str(spec["id"]))

    rooms: dict[str, Room] = {}
    for location in plan_locations:
        room_id = str(location["id"])
        rooms[room_id] = Room(
            id=room_id,
            name=str(location["name"]),
            description=str(location["description"]),
            exits=dict(location["exits"]),
            item_ids=tuple(items_by_room[room_id]),
            npc_ids=tuple(npc_ids_by_room[room_id]),
        )

    opening_inventory = tuple(str(item_id) for item_id in protagonist["inventory"])
    player = PlayerState(
        location=str(protagonist["location_id"]),
        inventory=opening_inventory,
        flags={"started": True},
    )
    world = WorldState(rooms=rooms, items=items, npcs=npcs)
    world_package = {
        "bootstrap_plan": dict(plan),
        "trigger_specs": tuple(plan["triggers"]),
        "outline": {"id": str(plan["outline_id"]), "source_text": ""},
        "goals": {
            "setup": "",
            "primary": next(
                (str(goal["summary"]) for goal in plan["goals"] if str(goal["kind"]) == "primary"),
                "",
            ),
            "secondary": tuple(
                str(goal["summary"]) for goal in plan["goals"] if str(goal["kind"]) not in {"primary", "setup"}
            ),
        },
    }
    state = GameState(
        seed=seed,
        player=player,
        world=world,
        story_genre="bootstrap",
        story_tone=tone,
        session_length=session_length,
        plot_curve_id="bootstrap_dynamic",
        story_outline_id=str(plan["outline_id"]),
        world_package=world_package,
        active_goal=next((str(goal["summary"]) for goal in plan["goals"] if str(goal["status"]) == "active"), ""),
    )
    initialize_world_facts(state)

    for spec in plan_characters:
        if spec["id"] == protagonist_id:
            continue
        state.world_facts.assert_fact("npc_role", str(spec["name"]), str(spec["role"]))
        for trait in spec["stable_traits"]:
            state.world_facts.assert_fact("npc_stable_trait", str(spec["id"]), str(trait))
        for trait in spec["dynamic_traits"]:
            state.world_facts.assert_fact("npc_dynamic_trait", str(spec["id"]), str(trait))

    for spec in plan_items:
        holder_id = str(spec["holder_id"])
        if holder_id:
            holder = "player" if holder_id == protagonist_id else holder_id
            state.world_facts.assert_fact("holding", holder, str(spec["id"]))
        for trait in spec["stable_traits"]:
            state.world_facts.assert_fact("item_stable_trait", str(spec["id"]), str(trait))
        for trait in spec["dynamic_traits"]:
            state.world_facts.assert_fact("item_dynamic_trait", str(spec["id"]), str(trait))

    story_goal_facts = tuple(("story_goal", str(goal["kind"]), str(goal["summary"])) for goal in plan["goals"])
    replace_fact_group(state, "story_goal", story_goal_facts)
    if protagonist["name"]:
        replace_fact_group(state, "player_name", (("player_name", str(protagonist["name"])),))
    active_goal = next((str(goal["summary"]) for goal in plan["goals"] if str(goal["status"]) == "active"), "")
    if active_goal:
        set_active_story_goal(state, active_goal)
    assistant = next((character for character in plan_characters if str(character["role"]) == "assistant"), None)
    if assistant is not None:
        assistant_name = str(assistant["name"]).strip()
        if assistant_name:
            replace_fact_group(state, "assistant_name", (("assistant_name", assistant_name),))
            state.world_facts.assert_fact("npc_relationship", assistant_name, "player", "assistant")

    sync_legacy_views(state)
    return state
