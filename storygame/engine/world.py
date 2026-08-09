from __future__ import annotations

import re

from storygame.engine.bootstrap import validate_bootstrap_plan
from storygame.engine.facts import (
    apply_fact_ops,
    initialize_world_facts,
    replace_fact_group,
    set_active_story_goal,
    sync_legacy_views,
)
from storygame.engine.npc import ensure_default_role_contracts
from storygame.engine.scene_state import refresh_scene_state
from storygame.engine.state import GameState, Item, Npc, PlayerState, Room, WorldState
from storygame.engine.world_builder import build_world_package
from storygame.test_metrics import record


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


def _build_items(package: dict) -> dict[str, Item]:
    specs = tuple(package["items"])
    items = {
        str(spec["id"]): Item(
            id=str(spec["id"]),
            name=str(spec["name"]),
            description=str(spec["description"]),
            portable=bool(spec.get("portable", True)),
            tags=tuple(map(str, spec.get("tags", []))),
            kind=str(spec.get("kind", "object")),
            clue_text=str(spec.get("clue_text", "")),
        )
        for spec in specs
        if str(spec.get("kind", "object")) != "vehicle"
    }
    items["field_kit"] = Item(
        id="field_kit",
        name="Field Kit",
        description="Basic tools packed before the journey began.",
        tags=("tool",),
        kind="tool",
    )
    items.update(
        {
            str(spec["id"]): Item(
                id=str(spec["id"]),
                name=str(spec["name"]),
                description=str(spec["description"]),
                portable=bool(spec.get("portable", True)),
                tags=tuple(map(str, spec.get("tags", []))),
                kind=str(spec.get("kind", "object")),
                clue_text=str(spec.get("clue_text", "")),
            )
            for spec in specs
            if str(spec.get("kind", "object")) == "vehicle"
        }
    )
    return items


def _build_npcs(package: dict) -> dict[str, Npc]:
    return {
        str(spec["id"]): Npc(
            id=str(spec["id"]),
            name=str(spec["name"]),
            description=str(spec.get("description", spec["name"])),
            dialogue=str(spec.get("dialogue", "")),
            identity=str(spec.get("role", "participant")),
            appearance=str(spec.get("appearance", "")),
            pronouns=str(spec.get("pronouns", "")).strip() or _infer_binary_pronouns(str(spec["name"])),
            tags=tuple(map(str, spec.get("traits", []))),
        )
        for spec in package["characters"]
    }


def _build_room_exits(paths: tuple[dict, ...] | list[dict]) -> dict[str, dict[str, str]]:
    exits: dict[str, dict[str, str]] = {}
    for path in paths:
        exits.setdefault(path["from"], {})[path["direction"]] = path["to"]
    return exits


def _build_rooms(package: dict) -> dict[str, Room]:
    room_ids = tuple(package["map"]["rooms"])
    exits = _build_room_exits(tuple(package["map"]["paths"]))
    rooms: dict[str, Room] = {}
    presentation = package["map"]["room_presentation"]
    for room_id in room_ids:
        copy = presentation[room_id]
        rooms[room_id] = Room(
            id=room_id,
            name=str(copy["name"]),
            description=str(copy["description"]),
            exits=dict(exits.get(room_id, {})),
        )
    for lock in package["map"].get("locks", []):
        room = rooms[str(lock["room"])]
        room.locked_exits[str(lock["direction"])] = str(lock["key_id"])
    return rooms


def _apply_opening_setup(state: GameState, package: dict) -> None:
    setup = dict(package.get("opening_setup", {}))
    protagonist_name = str(setup.get("protagonist_name", "")).strip()
    contact = dict(setup.get("opening_contact", {}))
    contact_id = str(contact.get("id", "")).strip()
    if not contact_id and "index" in contact:
        opening_order = tuple(map(str, setup.get("arrival_order", ())))
        index = int(contact.get("index", -1))
        if 0 <= index < len(opening_order):
            contact_id = opening_order[index]
    contact_npc = state.world.npcs.get(contact_id)
    ops: list[dict[str, object]] = []
    if protagonist_name:
        ops.append({"op": "assert", "fact": ("player_name", protagonist_name)})
    if contact_npc is not None:
        role = str(contact.get("role", "")).strip()
        relationship = str(contact.get("relationship", "")).strip()
        purpose = str(contact.get("scene_purpose", "")).strip()
        if role:
            ops.extend(
                (
                    {"op": "assert", "fact": ("assistant_name", contact_npc.name)},
                    {"op": "assert", "fact": ("npc_role", contact_npc.name, role)},
                )
            )
        if relationship:
            ops.append({"op": "assert", "fact": ("npc_relationship", contact_npc.name, "player", relationship)})
        if purpose:
            ops.append({"op": "assert", "fact": ("npc_scene_purpose", contact_id, purpose)})
    ops.extend(
        {"op": "assert", "fact": ("player_context", key, value)}
        for key, value in dict(setup.get("player_context", {})).items()
    )
    ops.extend(
        {"op": "assert", "fact": ("case_fact", key, value)} for key, value in dict(setup.get("case_facts", {})).items()
    )
    if ops:
        apply_fact_ops(state, ops)


def _place_package_entities(package: dict, rooms: dict[str, Room]) -> tuple[str, ...]:
    player_inventory = ["field_kit"]
    for character in package["characters"]:
        room = rooms[str(character["location"])]
        room.npc_ids = (*room.npc_ids, str(character["id"]))
    for item in package["items"]:
        custody = item.get("initial_custody") or {}
        item_id = str(item["id"])
        if custody.get("kind") == "room":
            room = rooms[str(custody["id"])]
            room.item_ids = (*room.item_ids, item_id)
        elif custody.get("kind") == "player":
            player_inventory.append(item_id)
    return tuple(dict.fromkeys(player_inventory))


def _package_fact_ops(package: dict) -> list[dict[str, object]]:
    ops: list[dict[str, object]] = []
    for item in package["items"]:
        item_id = str(item["id"])
        custody = item.get("initial_custody") or {}
        if custody.get("kind") == "npc":
            ops.append({"op": "assert", "fact": ("holding", str(custody["id"]), item_id)})
        state = str(item.get("initial_state", "")).strip()
        if state:
            ops.append({"op": "assert", "fact": ("item_state", item_id, state)})
        for predicate in ("item_owner", "item_driver"):
            value = str(item.get(predicate.removeprefix("item_"), "")).strip()
            if value:
                ops.append({"op": "assert", "fact": (predicate, item_id, value)})
    for character in package["characters"]:
        npc_id = str(character["id"])
        for knowledge in character.get("initial_knowledge", []):
            ops.append({"op": "assert", "fact": ("knows", npc_id, str(knowledge))})
        for knowledge in character.get("protected_knowledge", []):
            ops.append({"op": "assert", "fact": ("conceals", npc_id, str(knowledge))})
        relationship = str(character.get("relationship", "")).strip()
        if relationship:
            ops.append({"op": "assert", "fact": ("npc_relationship", str(character["name"]), "player", relationship)})
        purpose = str(character.get("scene_purpose", "")).strip()
        if purpose:
            ops.append({"op": "assert", "fact": ("npc_scene_purpose", npc_id, purpose)})
    return ops


def realize_world_package(package: dict, seed: int) -> GameState:
    """Realize validated package data into a fact-backed playable world."""
    items = _build_items(package)
    npcs = _build_npcs(package)
    rooms = _build_rooms(package)

    start_room = package["map"]["rooms"][0]
    player = PlayerState(
        location=start_room, inventory=_place_package_entities(package, rooms), flags={"started": True}
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
    ops = _package_fact_ops(package)
    if ops:
        apply_fact_ops(state, ops)
    _apply_opening_setup(state, package)
    ensure_default_role_contracts(state)
    sync_legacy_views(state)
    refresh_scene_state(state)
    return state


def build_default_state(
    seed: int, genre: str = "mystery", session_length: int | str = "medium", tone: str = "neutral"
) -> GameState:
    record("full_world_build", genre=genre)
    return realize_world_package(build_world_package(genre, session_length, seed, tone), seed)


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

    bootstrap_ops: list[dict[str, object]] = []
    for spec in plan_characters:
        if spec["id"] == protagonist_id:
            continue
        bootstrap_ops.append({"op": "assert", "fact": ("npc_role", str(spec["name"]), str(spec["role"]))})
        for trait in spec["stable_traits"]:
            bootstrap_ops.append({"op": "assert", "fact": ("npc_stable_trait", str(spec["id"]), str(trait))})
        for trait in spec["dynamic_traits"]:
            bootstrap_ops.append({"op": "assert", "fact": ("npc_dynamic_trait", str(spec["id"]), str(trait))})

    for spec in plan_items:
        holder_id = str(spec["holder_id"])
        if holder_id:
            holder = "player" if holder_id == protagonist_id else holder_id
            bootstrap_ops.append({"op": "assert", "fact": ("holding", holder, str(spec["id"]))})
        for trait in spec["stable_traits"]:
            bootstrap_ops.append({"op": "assert", "fact": ("item_stable_trait", str(spec["id"]), str(trait))})
        for trait in spec["dynamic_traits"]:
            bootstrap_ops.append({"op": "assert", "fact": ("item_dynamic_trait", str(spec["id"]), str(trait))})

    if bootstrap_ops:
        apply_fact_ops(state, bootstrap_ops)

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
            apply_fact_ops(
                state, [{"op": "assert", "fact": ("npc_relationship", assistant_name, "player", "assistant")}]
            )

    ensure_default_role_contracts(state)
    sync_legacy_views(state)
    refresh_scene_state(state)
    return state
