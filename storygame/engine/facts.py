from __future__ import annotations

from typing import Any

Fact = tuple[str, ...]
FactOp = dict[str, Any]
_LEGACY_FACT_PREDICATES = {
    "at",
    "holding",
    "flag",
    "room_name",
    "room_description",
    "path",
    "locked",
    "room_item",
    "npc_at",
    "item_name",
    "item_kind",
    "item_description",
    "clue_text",
    "npc_name",
    "npc_trait",
    "npc_identity",
    "npc_pronouns",
}


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
        facts.assert_fact("room_name", room_id, room.name)
        facts.assert_fact("room_description", room_id, room.description)
        for direction, destination in room.exits.items():
            facts.assert_fact("path", direction, room_id, destination)
        for direction, key_id in room.locked_exits.items():
            facts.assert_fact("locked", direction, room_id, key_id)
        for item_id in room.item_ids:
            facts.assert_fact("room_item", room_id, item_id)
        for npc_id in room.npc_ids:
            facts.assert_fact("npc_at", npc_id, room_id)
    for item_id, item in state.world.items.items():
        facts.assert_fact("item_name", item_id, item.name)
        facts.assert_fact("item_kind", item_id, item.kind)
        facts.assert_fact("item_description", item_id, item.description)
        if item.clue_text:
            facts.assert_fact("clue_text", item_id, item.clue_text)
    for npc_id, npc in state.world.npcs.items():
        facts.assert_fact("npc_name", npc_id, npc.name)
        facts.assert_fact("npc_trait", npc_id, npc.description)
        if npc.identity:
            facts.assert_fact("npc_identity", npc_id, npc.identity)
        if npc.pronouns:
            facts.assert_fact("npc_pronouns", npc_id, npc.pronouns)
    state.world_facts = facts


def rebuild_facts_from_legacy_views(state) -> None:
    preserved = tuple(fact for fact in state.world_facts.all() if fact[0] not in _LEGACY_FACT_PREDICATES)
    initialize_world_facts(state)
    for fact in preserved:
        state.world_facts.assert_fact(fact[0], *fact[1:])


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


def replace_fact_group(state, predicate: str, facts: tuple[Fact, ...]) -> None:
    existing = tuple(fact for fact in state.world_facts.all() if fact and fact[0] == predicate)
    for fact in existing:
        state.world_facts.retract_fact(fact[0], *fact[1:])
    for fact in facts:
        state.world_facts.assert_fact(fact[0], *fact[1:])


def active_story_goal(state) -> str:
    facts = state.world_facts.query("active_goal", None)
    if facts:
        return facts[0][1]
    return state.active_goal


def set_active_story_goal(state, goal: str) -> None:
    existing = tuple(fact for fact in state.world_facts.query("active_goal", None))
    for fact in existing:
        state.world_facts.retract_fact(fact[0], *fact[1:])
    if goal.strip():
        state.world_facts.assert_fact("active_goal", goal.strip())


def story_goals(state) -> dict[str, object]:
    setup = tuple(fact[2] for fact in state.world_facts.query("story_goal", "setup", None))
    primary = tuple(fact[2] for fact in state.world_facts.query("story_goal", "primary", None))
    secondary = tuple(fact[2] for fact in state.world_facts.query("story_goal", "secondary", None))
    return {
        "setup": setup[0] if setup else "",
        "primary": primary[0] if primary else "",
        "secondary": secondary,
    }


def assistant_role(state, assistant_name: str) -> str:
    normalized = assistant_name.strip().lower()
    if not normalized:
        return ""
    for fact in state.world_facts.query("npc_role", None, None):
        if fact[1].strip().lower() == normalized:
            return fact[2]
    return ""


def assistant_name(state) -> str:
    named_facts = state.world_facts.query("assistant_name", None)
    if named_facts:
        return named_facts[0][1]
    for fact in state.world_facts.query("npc_role", None, None):
        if fact[2].strip().lower() == "assistant":
            return fact[1]
    return ""


def protagonist_profile(state) -> dict[str, str]:
    name_facts = state.world_facts.query("player_name", None)
    background_facts = state.world_facts.query("player_background", None)
    return {
        "name": name_facts[0][1] if name_facts else "",
        "background": background_facts[0][1] if background_facts else "",
    }


def hidden_story_threads(state) -> tuple[str, ...]:
    return tuple(fact[1] for fact in state.world_facts.query("story_hidden_thread", None))


def reveal_schedule(state) -> tuple[dict[str, float], ...]:
    return tuple(
        {
            "thread_index": int(fact[1]),
            "min_progress": float(fact[2]),
        }
        for fact in state.world_facts.query("story_reveal_schedule", None, None)
    )


def planned_story_events(state) -> tuple[dict[str, object], ...]:
    participants_by_event: dict[str, list[str]] = {}
    for fact in state.world_facts.query("planned_event_participant", None, None):
        participants_by_event.setdefault(fact[1], []).append(fact[2])
    return tuple(
        {
            "event_id": fact[1],
            "summary": fact[2],
            "min_turn": int(fact[3]),
            "location": fact[4],
            "participants": tuple(participants_by_event.get(fact[1], ())),
        }
        for fact in state.world_facts.query("planned_event", None, None, None, None)
    )


def discovered_leads(state) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "subject": fact[1],
            "text": fact[2],
        }
        for fact in state.world_facts.query("discovered_lead", None, None)
    )


def npc_location(state, npc_id: str) -> str:
    locations = state.world_facts.query("npc_at", npc_id, None)
    if locations:
        return locations[0][2]
    return ""


def apply_fact_ops(state, ops: list[FactOp] | tuple[FactOp, ...]) -> None:
    for op in ops:
        if op["op"] == "assert":
            predicate, *terms = op["fact"]
            if predicate == "npc_at" and len(terms) == 2:
                for fact in state.world_facts.query("npc_at", terms[0], None):
                    state.world_facts.retract_fact(fact[0], *fact[1:])
            if predicate == "at" and len(terms) == 2 and terms[0] == "player":
                for fact in state.world_facts.query("at", "player", None):
                    state.world_facts.retract_fact(fact[0], *fact[1:])
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
