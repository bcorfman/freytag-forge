from __future__ import annotations

from typing import Any


Fact = tuple[str, ...]
FactOp = dict[str, Any]

class ProjectionUpdater:
    def refresh_from_facts(self, state) -> None:
        player_locations = state.world_facts.query("at", "player", None)
        if player_locations:
            state.player.location = player_locations[0][2]

        state.player.inventory = tuple(fact[2] for fact in state.world_facts.query("holding", "player", None))
        merged_flags = dict(state.player.flags)
        for fact in state.world_facts.query("flag", "player", None):
            merged_flags[fact[2]] = True
        state.player.flags = merged_flags

        active_goals = state.world_facts.query("active_goal", None)
        if active_goals:
            state.active_goal = active_goals[0][1]

        for room_id, room in state.world.rooms.items():
            room.exits = {fact[1]: fact[3] for fact in state.world_facts.query("path", None, room_id, None)}
            room.locked_exits = {fact[1]: fact[3] for fact in state.world_facts.query("locked", None, room_id, None)}
            fact_item_ids = tuple(fact[2] for fact in state.world_facts.query("room_item", room_id, None))
            fact_npc_ids = tuple(fact[1] for fact in state.world_facts.query("npc_at", None, room_id))
            room.item_ids = self._preserve_room_order(room.item_ids, fact_item_ids)
            room.npc_ids = self._preserve_room_order(room.npc_ids, fact_npc_ids)

    def _preserve_room_order(self, current_ids: tuple[str, ...], fact_ids: tuple[str, ...]) -> tuple[str, ...]:
        ordered = [entity_id for entity_id in current_ids if entity_id in fact_ids]
        ordered.extend(entity_id for entity_id in fact_ids if entity_id not in ordered)
        return tuple(ordered)


class InvariantValidator:
    def validate_pre_commit(self, state, ops: list[FactOp] | tuple[FactOp, ...]) -> tuple[FactOp, ...]:
        working_facts = set(state.world_facts.all())
        normalized_ops = list(self._normalize_existing_facts(working_facts))

        for op in ops:
            operation = str(op["op"])
            if operation == "assert":
                fact = tuple(str(term) for term in op["fact"])
                for existing in self._facts_to_replace(working_facts, fact):
                    working_facts.discard(existing)
                    normalized_ops.append({"op": "retract", "fact": existing})
                working_facts.add(fact)
                normalized_ops.append({"op": "assert", "fact": fact})
                continue

            if operation == "retract":
                fact = tuple(str(term) for term in op["fact"])
                working_facts.discard(fact)
                normalized_ops.append({"op": "retract", "fact": fact})
                continue

            if operation == "numeric_delta":
                normalized_ops.append({"op": "numeric_delta", "key": str(op["key"]), "delta": float(op["delta"])})
                continue

            raise ValueError(f"Unsupported fact op '{operation}'.")

        self._validate_facts(working_facts)
        return tuple(normalized_ops)

    def _normalize_existing_facts(self, facts: set[Fact]) -> tuple[FactOp, ...]:
        containers_by_item: dict[str, list[Fact]] = {}
        normalized_ops: list[FactOp] = []
        for fact in facts:
            if fact[0] in {"holding", "room_item"} and len(fact) == 3:
                containers_by_item.setdefault(fact[2], []).append(fact)

        for item_id, containers in containers_by_item.items():
            if len(containers) <= 1:
                continue
            holding_facts = [fact for fact in containers if fact[0] == "holding"]
            preferred = holding_facts[0] if holding_facts else containers[0]
            for fact in containers:
                if fact != preferred:
                    facts.discard(fact)
                    normalized_ops.append({"op": "retract", "fact": fact})
        return tuple(normalized_ops)

    def _facts_to_replace(self, facts: set[Fact], fact: Fact) -> tuple[Fact, ...]:
        predicate = fact[0]
        terms = fact[1:]

        if predicate == "npc_at" and len(terms) == 2:
            return tuple(existing for existing in facts if existing[:2] == ("npc_at", terms[0]))
        if predicate == "at" and len(terms) == 2 and terms[0] == "player":
            return tuple(existing for existing in facts if existing[:2] == ("at", "player"))
        if predicate == "holding" and len(terms) == 2:
            item_id = terms[1]
            return tuple(
                existing
                for existing in facts
                if (existing[0] == "holding" and len(existing) >= 3 and existing[2] == item_id)
                or (existing[0] == "room_item" and len(existing) >= 3 and existing[2] == item_id)
            )
        if predicate == "room_item" and len(terms) == 2:
            item_id = terms[1]
            return tuple(
                existing
                for existing in facts
                if (existing[0] == "room_item" and len(existing) >= 3 and existing[2] == item_id)
                or (existing[0] == "holding" and len(existing) >= 3 and existing[2] == item_id)
            )
        if predicate == "active_goal" and len(terms) == 1:
            return tuple(existing for existing in facts if existing[0] == "active_goal")
        if predicate == "assistant_name" and len(terms) == 1:
            return tuple(existing for existing in facts if existing[0] == "assistant_name")
        if predicate == "player_name" and len(terms) == 1:
            return tuple(existing for existing in facts if existing[0] == "player_name")
        if predicate == "player_background" and len(terms) == 1:
            return tuple(existing for existing in facts if existing[0] == "player_background")
        if predicate == "npc_role" and len(terms) == 2:
            return tuple(existing for existing in facts if existing[:2] == ("npc_role", terms[0]))

        return ()

    def _validate_facts(self, facts: set[Fact]) -> None:
        self._validate_player_location(facts)
        self._validate_npc_locations(facts)
        self._validate_item_containers(facts)
        self._validate_active_goal(facts)
        self._validate_roles(facts)

    def _validate_player_location(self, facts: set[Fact]) -> None:
        player_locations = {fact[2] for fact in facts if fact[:2] == ("at", "player") and len(fact) == 3}
        if len(player_locations) > 1:
            raise ValueError("player location must remain unique")

    def _validate_npc_locations(self, facts: set[Fact]) -> None:
        locations_by_npc: dict[str, set[str]] = {}
        for fact in facts:
            if fact[0] != "npc_at" or len(fact) != 3:
                continue
            locations_by_npc.setdefault(fact[1], set()).add(fact[2])
        for npc_id, locations in locations_by_npc.items():
            if len(locations) > 1:
                raise ValueError(f"npc '{npc_id}' has multiple locations")

    def _validate_item_containers(self, facts: set[Fact]) -> None:
        containers_by_item: dict[str, set[tuple[str, str]]] = {}
        for fact in facts:
            if fact[0] == "holding" and len(fact) == 3:
                containers_by_item.setdefault(fact[2], set()).add(("holding", fact[1]))
            if fact[0] == "room_item" and len(fact) == 3:
                containers_by_item.setdefault(fact[2], set()).add(("room_item", fact[1]))
        for item_id, containers in containers_by_item.items():
            if len(containers) > 1:
                raise ValueError(f"item '{item_id}' has multiple canonical containers")

    def _validate_active_goal(self, facts: set[Fact]) -> None:
        active_goals = {fact[1] for fact in facts if fact[0] == "active_goal" and len(fact) == 2}
        if len(active_goals) > 1:
            raise ValueError("active_goal must remain unique")

    def _validate_roles(self, facts: set[Fact]) -> None:
        roles_by_name: dict[str, set[str]] = {}
        for fact in facts:
            if fact[0] != "npc_role" or len(fact) != 3:
                continue
            roles_by_name.setdefault(fact[1].strip().lower(), set()).add(fact[2].strip().lower())
        for name, roles in roles_by_name.items():
            if len(roles) > 1:
                raise ValueError(f"npc '{name}' has conflicting canonical roles")


class ValidatedFactCommitter:
    def __init__(
        self,
        validator: InvariantValidator | None = None,
        projection_updater: ProjectionUpdater | None = None,
    ) -> None:
        self._validator = InvariantValidator() if validator is None else validator
        self._projection_updater = ProjectionUpdater() if projection_updater is None else projection_updater

    def commit(self, state, ops: list[FactOp] | tuple[FactOp, ...], source: str = "runtime") -> tuple[FactOp, ...]:
        try:
            normalized_ops = self._validator.validate_pre_commit(state, ops)
        except ValueError as exc:
            raise ValueError(f"{source}: {exc}") from exc

        for op in normalized_ops:
            operation = op["op"]
            if operation == "assert":
                predicate, *terms = op["fact"]
                state.world_facts.assert_fact(predicate, *terms)
                if predicate == "flag" and len(terms) == 2 and terms[0] == "player":
                    state.player.flags[terms[1]] = True
                continue
            if operation == "retract":
                predicate, *terms = op["fact"]
                state.world_facts.retract_fact(predicate, *terms)
                if predicate == "flag" and len(terms) == 2 and terms[0] == "player":
                    state.player.flags[terms[1]] = False
                continue
            if operation == "numeric_delta":
                key = str(op["key"])
                delta = float(op["delta"])
                state.fact_metrics[key] = state.fact_metrics.get(key, 0.0) + delta
                continue
            raise ValueError(f"{source}: Unsupported fact op '{operation}'.")

        self._projection_updater.refresh_from_facts(state)
        return normalized_ops
