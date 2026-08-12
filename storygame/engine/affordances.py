"""Fact-derived legal interaction context for story-model proposals."""

from __future__ import annotations

from storygame.engine.facts import player_inventory, player_location, room_items, room_npcs, room_paths


def build_affordance_context(state, observer: str = "player") -> dict[str, object]:
    location_id = player_location(state) if observer == "player" else _npc_location(state, observer)
    held = (
        set(player_inventory(state))
        if observer == "player"
        else {fact[2] for fact in state.world_facts.query("holding", observer, None)}
    )
    exits = []
    for route_id, destination in sorted(room_paths(state, location_id).items()):
        locks = state.world_facts.query("locked", route_id, location_id, None)
        required = locks[0][3] if locks else ""
        entry = {"destination": destination, "locked": bool(required and required not in held)}
        label = next((str(fact[3]) for fact in state.world_facts.query("path_label", location_id, route_id, None)), "")
        if label:
            entry["label"] = label
        exits.append(entry)
    items = []
    for item_id in room_items(state, location_id):
        item = state.world.items.get(item_id)
        if item is not None:
            entry: dict[str, object] = {"id": item_id, "portable": bool(item.portable)}
            affordances = tuple(fact[2] for fact in state.world_facts.query("item_affordance", item_id, None))
            aliases = tuple(fact[2] for fact in state.world_facts.query("item_alias", item_id, None))
            if affordances:
                entry["affordances"] = affordances
            if aliases:
                entry["aliases"] = aliases
            items.append(entry)
    npcs = tuple({"id": npc_id, "can_address": True} for npc_id in room_npcs(state, location_id) if npc_id != observer)
    return {
        "observer": observer,
        "location_id": location_id,
        "exits": tuple(exits),
        "items": tuple(items),
        "npcs": npcs,
        "inventory": tuple(sorted(held)),
    }


def _npc_location(state, npc_id: str) -> str:
    facts = state.world_facts.query("npc_at", npc_id, None)
    return facts[0][2] if facts else ""
