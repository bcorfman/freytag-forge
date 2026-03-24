from __future__ import annotations

from storygame.llm.bootstrap_contracts import BootstrapPlan


def validate_bootstrap_plan(plan: BootstrapPlan) -> None:
    location_ids = {entry["id"] for entry in plan["locations"]}
    if len(location_ids) != len(plan["locations"]):
        raise ValueError("Bootstrap plan contains duplicate location ids.")

    character_ids = {entry["id"] for entry in plan["characters"]}
    if len(character_ids) != len(plan["characters"]):
        raise ValueError("Bootstrap plan contains duplicate character ids.")

    item_ids = {entry["id"] for entry in plan["items"]}
    if len(item_ids) != len(plan["items"]):
        raise ValueError("Bootstrap plan contains duplicate item ids.")

    if plan["protagonist_id"] not in character_ids:
        raise ValueError(f"Unknown protagonist_id '{plan['protagonist_id']}'.")

    for location in plan["locations"]:
        for destination in location["exits"].values():
            if destination not in location_ids:
                raise ValueError(f"Unknown exit destination '{destination}' in location '{location['id']}'.")

    for character in plan["characters"]:
        if character["location_id"] not in location_ids:
            raise ValueError(f"Unknown location '{character['location_id']}' for character '{character['id']}'.")
        for item_id in character["inventory"]:
            if item_id not in item_ids:
                raise ValueError(f"Unknown inventory item '{item_id}' for character '{character['id']}'.")

    for item in plan["items"]:
        has_location = bool(item["location_id"])
        has_holder = bool(item["holder_id"])
        if has_location == has_holder:
            raise ValueError(
                f"Item '{item['id']}' must reference exactly one placement target; "
                f"got location='{item['location_id']}' holder='{item['holder_id']}'."
            )
        if has_location and item["location_id"] not in location_ids:
            raise ValueError(f"Unknown location '{item['location_id']}' for item '{item['id']}'.")
        if has_holder and item["holder_id"] not in character_ids:
            raise ValueError(f"Unknown holder '{item['holder_id']}' for item '{item['id']}'.")

    goal_ids = {goal["goal_id"] for goal in plan["goals"]}
    if len(goal_ids) != len(plan["goals"]):
        raise ValueError("Bootstrap plan contains duplicate goal ids.")

    trigger_ids: set[str] = set()
    for trigger in plan["triggers"]:
        if trigger["trigger_id"] in trigger_ids:
            raise ValueError(f"Duplicate trigger id '{trigger['trigger_id']}'.")
        trigger_ids.add(trigger["trigger_id"])
        unknown_actor = next((actor_id for actor_id in trigger["actor_ids"] if actor_id not in character_ids and actor_id != "player"), "")
        if unknown_actor:
            raise ValueError(f"Unknown actor id '{unknown_actor}' in trigger '{trigger['trigger_id']}'.")
        unknown_target = next(
            (target_id for target_id in trigger["target_ids"] if target_id not in character_ids and target_id != "player"),
            "",
        )
        if unknown_target:
            raise ValueError(f"Unknown target id '{unknown_target}' in trigger '{trigger['trigger_id']}'.")
        unknown_item = next((item_id for item_id in trigger["item_ids"] if item_id not in item_ids), "")
        if unknown_item:
            raise ValueError(f"Unknown item id '{unknown_item}' in trigger '{trigger['trigger_id']}'.")
        unknown_location = next((location_id for location_id in trigger["location_ids"] if location_id not in location_ids), "")
        if unknown_location:
            raise ValueError(f"Unknown location id '{unknown_location}' in trigger '{trigger['trigger_id']}'.")
