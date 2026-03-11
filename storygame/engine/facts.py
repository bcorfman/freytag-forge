from __future__ import annotations

from typing import Any

Fact = tuple[str, ...]
FactOp = dict[str, Any]


class FactStore:
    def __init__(self, facts: set[Fact] | None = None) -> None:
        self._facts: set[Fact] = set() if facts is None else set(facts)

    def assert_fact(self, predicate: str, *terms: str) -> None:
        self._facts.add((predicate, *terms))

    def retract_fact(self, predicate: str, *terms: str) -> None:
        self._facts.discard((predicate, *terms))

    def holds(self, predicate: str, *terms: str) -> bool:
        return (predicate, *terms) in self._facts

    def query(self, predicate: str, *pattern: str | None) -> tuple[Fact, ...]:
        results: list[Fact] = []
        for fact in self._facts:
            if fact[0] != predicate:
                continue
            if len(pattern) > len(fact) - 1:
                continue
            matched = True
            for index, token in enumerate(pattern):
                if token is not None and fact[index + 1] != token:
                    matched = False
                    break
            if matched:
                results.append(fact)
        return tuple(sorted(results))

    def all(self) -> tuple[Fact, ...]:
        return tuple(sorted(self._facts))

    def replace_all(self, facts: tuple[Fact, ...]) -> None:
        self._facts = set(facts)


def initialize_world_facts(state) -> None:
    facts = FactStore()
    facts.assert_fact("at", "player", state.player.location)
    for item_id in state.player.inventory:
        facts.assert_fact("holding", "player", item_id)
    for flag_name, enabled in state.player.flags.items():
        if enabled:
            facts.assert_fact("flag", "player", flag_name)

    for room_id, room in state.world.rooms.items():
        for direction, destination in room.exits.items():
            facts.assert_fact("path", direction, room_id, destination)
        for direction, key_id in room.locked_exits.items():
            facts.assert_fact("locked", direction, room_id, key_id)
        for item_id in room.item_ids:
            facts.assert_fact("room_item", room_id, item_id)
        for npc_id in room.npc_ids:
            facts.assert_fact("npc_at", npc_id, room_id)
    state.world_facts = facts


def rebuild_facts_from_legacy_views(state) -> None:
    initialize_world_facts(state)


def player_location(state) -> str:
    locations = state.world_facts.query("at", "player", None)
    if locations:
        return locations[0][2]
    return state.player.location


def player_inventory(state) -> tuple[str, ...]:
    held = state.world_facts.query("holding", "player", None)
    return tuple(fact[2] for fact in held)


def player_flags(state) -> dict[str, bool]:
    flags = state.world_facts.query("flag", "player", None)
    return {fact[2]: True for fact in flags}


def room_items(state, room_id: str) -> tuple[str, ...]:
    return tuple(fact[2] for fact in state.world_facts.query("room_item", room_id, None))


def room_npcs(state, room_id: str) -> tuple[str, ...]:
    return tuple(fact[1] for fact in state.world_facts.query("npc_at", None, room_id))


def room_paths(state, room_id: str) -> dict[str, str]:
    return {fact[1]: fact[3] for fact in state.world_facts.query("path", None, room_id, None)}


def room_locked(state, room_id: str) -> dict[str, str]:
    return {fact[1]: fact[3] for fact in state.world_facts.query("locked", None, room_id, None)}


def sync_legacy_views(state) -> None:
    state.player.location = player_location(state)
    state.player.inventory = player_inventory(state)
    state.player.flags = player_flags(state)

    for room_id, room in state.world.rooms.items():
        room.exits = room_paths(state, room_id)
        room.locked_exits = room_locked(state, room_id)
        room.item_ids = room_items(state, room_id)
        room.npc_ids = room_npcs(state, room_id)


def apply_fact_ops(state, ops: list[FactOp] | tuple[FactOp, ...]) -> None:
    for op in ops:
        if op["op"] == "assert":
            predicate, *terms = op["fact"]
            state.world_facts.assert_fact(predicate, *terms)
            continue
        if op["op"] == "retract":
            predicate, *terms = op["fact"]
            state.world_facts.retract_fact(predicate, *terms)
            continue
        if op["op"] == "numeric_delta":
            key = str(op["key"])
            delta = float(op["delta"])
            state.fact_metrics[key] = state.fact_metrics.get(key, 0.0) + delta
            continue
        raise ValueError(f"Unsupported fact op '{op['op']}'.")
    sync_legacy_views(state)


def event_fact_ops(event) -> tuple[FactOp, ...]:
    metadata = event.metadata
    if "fact_ops" not in metadata:
        return ()
    return tuple(metadata["fact_ops"])
