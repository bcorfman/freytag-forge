from __future__ import annotations

from typing import Any

from storygame.engine.fact_commit import ProjectionUpdater, ValidatedFactCommitter

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
    "npc_appearance",
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
        if npc.appearance:
            facts.assert_fact("npc_appearance", npc_id, npc.appearance)
        if npc.pronouns:
            facts.assert_fact("npc_pronouns", npc_id, npc.pronouns)
    state.world_facts = facts


def rebuild_facts_from_legacy_views(state) -> None:
    preserved = tuple(
        fact
        for fact in state.world_facts.all()
        if fact[0] not in _LEGACY_FACT_PREDICATES or (fact[0] == "holding" and len(fact) >= 3 and fact[1] != "player")
    )
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


def set_player_location(state, room_id: str) -> None:
    destination = room_id.strip()
    if not destination:
        return
    apply_fact_ops(state, [{"op": "assert", "fact": ("at", "player", destination)}])


def replace_player_inventory(state, item_ids: tuple[str, ...] | list[str]) -> None:
    existing = tuple(state.world_facts.query("holding", "player", None))
    ops: list[FactOp] = [{"op": "retract", "fact": fact} for fact in existing]
    for item_id in item_ids:
        normalized = str(item_id).strip()
        if normalized:
            ops.append({"op": "assert", "fact": ("holding", "player", normalized)})
    if ops:
        apply_fact_ops(state, ops)


def player_flags(state) -> dict[str, bool]:
    flags = state.world_facts.query("flag", "player", None)
    return {fact[2]: True for fact in flags}


def set_player_flag(state, flag_name: str, enabled: bool) -> None:
    normalized = flag_name.strip()
    if not normalized:
        return
    if enabled:
        apply_fact_ops(state, [{"op": "assert", "fact": ("flag", "player", normalized)}])
        return
    apply_fact_ops(state, [{"op": "retract", "fact": ("flag", "player", normalized)}])


def replace_player_flags(state, flags: dict[str, bool]) -> None:
    existing = tuple(state.world_facts.query("flag", "player", None))
    ops: list[FactOp] = [{"op": "retract", "fact": fact} for fact in existing]
    for flag_name, enabled in flags.items():
        normalized = str(flag_name).strip()
        if normalized and bool(enabled):
            ops.append({"op": "assert", "fact": ("flag", "player", normalized)})
    if ops:
        apply_fact_ops(state, ops)


def room_items(state, room_id: str) -> tuple[str, ...]:
    return tuple(fact[2] for fact in state.world_facts.query("room_item", room_id, None))


def replace_room_items(state, room_id: str, item_ids: tuple[str, ...] | list[str]) -> None:
    normalized_room_id = room_id.strip()
    if not normalized_room_id:
        return
    existing = tuple(state.world_facts.query("room_item", normalized_room_id, None))
    ops: list[FactOp] = [{"op": "retract", "fact": fact} for fact in existing]
    for item_id in item_ids:
        normalized_item_id = str(item_id).strip()
        if normalized_item_id:
            ops.append({"op": "assert", "fact": ("room_item", normalized_room_id, normalized_item_id)})
    if ops:
        apply_fact_ops(state, ops)


def room_npcs(state, room_id: str) -> tuple[str, ...]:
    return tuple(fact[1] for fact in state.world_facts.query("npc_at", None, room_id))


def room_paths(state, room_id: str) -> dict[str, str]:
    return {fact[1]: fact[3] for fact in state.world_facts.query("path", None, room_id, None)}


def room_locked(state, room_id: str) -> dict[str, str]:
    return {fact[1]: fact[3] for fact in state.world_facts.query("locked", None, room_id, None)}


def sync_legacy_views(state) -> None:
    ProjectionUpdater().refresh_from_facts(state)


def replace_fact_group(state, predicate: str, facts: tuple[Fact, ...]) -> None:
    existing = tuple(fact for fact in state.world_facts.all() if fact and fact[0] == predicate)
    ops: list[FactOp] = [{"op": "retract", "fact": fact} for fact in existing]
    ops.extend({"op": "assert", "fact": fact} for fact in facts)
    if ops:
        ValidatedFactCommitter().commit(state, ops, source=f"replace_fact_group:{predicate}")


def active_story_goal(state) -> str:
    facts = state.world_facts.query("active_goal", None)
    if facts:
        return facts[0][1]
    return state.active_goal


def current_scene(state) -> str:
    facts = state.world_facts.query("current_scene", None)
    if facts:
        return facts[0][1]
    return f"scene:{player_location(state)}"


def set_active_story_goal(state, goal: str) -> None:
    ops: list[FactOp] = [{"op": "retract", "fact": fact} for fact in state.world_facts.query("active_goal", None)]
    if goal.strip():
        ops.append({"op": "assert", "fact": ("active_goal", goal.strip())})
    if ops:
        ValidatedFactCommitter().commit(state, ops, source="set_active_story_goal")


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


def player_context_facts(state) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "key": fact[1],
            "text": fact[2],
        }
        for fact in state.world_facts.query("player_context", None, None)
    )


def case_facts(state) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "key": fact[1],
            "value": fact[2],
        }
        for fact in state.world_facts.query("case_fact", None, None)
    )


def villain_profiles(state) -> tuple[dict[str, str], ...]:
    motives = {fact[1]: fact[2] for fact in state.world_facts.query("villain_motive", None, None)}
    means = {fact[1]: fact[2] for fact in state.world_facts.query("villain_means", None, None)}
    opportunities = {fact[1]: fact[2] for fact in state.world_facts.query("villain_opportunity", None, None)}
    return tuple(
        {
            "name": fact[1],
            "motive": motives.get(fact[1], ""),
            "means": means.get(fact[1], ""),
            "opportunity": opportunities.get(fact[1], ""),
        }
        for fact in state.world_facts.query("villain", None)
    )


def npc_relationship_to_player(state, npc_name: str) -> str:
    normalized = npc_name.strip().lower()
    if not normalized:
        return ""
    for fact in state.world_facts.query("npc_relationship", None, "player", None):
        if fact[1].strip().lower() == normalized:
            return fact[3]
    return ""


def npc_scene_purpose(state, npc_id: str) -> str:
    facts = state.world_facts.query("npc_scene_purpose", npc_id, None)
    if facts:
        return facts[0][2]
    return ""


def item_owner(state, item_id: str) -> str:
    facts = state.world_facts.query("item_owner", item_id, None)
    if facts:
        return facts[0][2]
    return ""


def item_driver(state, item_id: str) -> str:
    facts = state.world_facts.query("item_driver", item_id, None)
    if facts:
        return facts[0][2]
    return ""


def item_state(state, item_id: str) -> str:
    facts = state.world_facts.query("item_state", item_id, None)
    if facts:
        return facts[0][2]
    return ""


def hidden_story_threads(state) -> tuple[str, ...]:
    return tuple(fact[1] for fact in state.world_facts.query("story_hidden_thread", None))


def scene_location(state, scene_id: str) -> str:
    facts = state.world_facts.query("scene_location", scene_id, None)
    if facts:
        return facts[0][2]
    return player_location(state)


def scene_objective(state, scene_id: str) -> str:
    facts = state.world_facts.query("scene_objective", scene_id, None)
    if facts:
        return facts[0][2]
    return active_story_goal(state)


def dramatic_question(state, scene_id: str) -> str:
    facts = state.world_facts.query("dramatic_question", scene_id, None)
    if facts:
        return facts[0][2]
    return ""


def scene_pressure(state, scene_id: str) -> str:
    facts = state.world_facts.query("scene_pressure", scene_id, None)
    if facts:
        return facts[0][2]
    return ""


def beat_phase(state) -> str:
    facts = state.world_facts.query("beat_phase", None)
    if facts:
        return facts[0][1]
    return ""


def beat_role(state, scene_id: str) -> str:
    facts = state.world_facts.query("beat_role", scene_id, None)
    if facts:
        return facts[0][2]
    return ""


def player_approach(state) -> str:
    facts = state.world_facts.query("player_approach", None)
    if facts:
        return facts[0][1]
    return ""


def scene_participants(state, scene_id: str) -> tuple[str, ...]:
    return tuple(fact[2] for fact in state.world_facts.query("scene_participant", scene_id, None))


def npc_stance_toward_player(state, npc_id: str) -> str:
    facts = state.world_facts.query("npc_stance", npc_id, "player", None)
    if facts:
        return facts[0][3]
    return ""


def npc_trust_toward_player(state, npc_id: str) -> str:
    facts = state.world_facts.query("npc_trust", npc_id, "player", None)
    if facts:
        return facts[0][3]
    return ""


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
    if ops:
        ValidatedFactCommitter().commit(state, ops, source="apply_fact_ops")


def event_fact_ops(event) -> tuple[FactOp, ...]:
    metadata = event.metadata
    if "fact_ops" not in metadata:
        return ()
    return tuple(metadata["fact_ops"])
