from __future__ import annotations

from dataclasses import dataclass

from storygame.engine.facts import player_location


@dataclass(frozen=True)
class Observation:
    observer: str
    entity: str
    exists: bool
    location: str
    accessible: bool
    perceptible: bool
    observed: bool
    recognized: bool
    interpreted: bool


class ObservationResolver:
    """Resolve what an observer may perceive from canonical facts only."""

    def __init__(self, state) -> None:
        self.state = state

    def resolve(self, observer: str, entity: str) -> Observation:
        observer_id = observer.strip()
        entity_id = entity.strip()
        exists = self._exists(entity_id)
        location = self._location(entity_id)
        observer_location = self._actor_location(observer_id)
        same_place = bool(location and location == observer_location)
        accessible = bool(
            same_place
            or self.state.world_facts.holds("holding", observer_id, entity_id)
            or self.state.world_facts.holds("accessible", observer_id, entity_id)
        )
        perceptible = exists and accessible and self._perceptible(observer_id, entity_id, location)
        return Observation(
            observer=observer_id,
            entity=entity_id,
            exists=exists,
            location=location,
            accessible=accessible,
            perceptible=perceptible,
            observed=self.state.world_facts.holds("observed", observer_id, entity_id),
            recognized=self.state.world_facts.holds("recognized", observer_id, entity_id),
            interpreted=bool(self.state.world_facts.query("interpreted", observer_id, entity_id, None)),
        )

    def validate_discovery(self, observer: str, entity: str, interpretation: str) -> None:
        observation = self.resolve(observer, entity)
        if not observation.perceptible or not observation.observed:
            raise ValueError("discovery requires observation of a perceptible entity")
        if not interpretation.strip():
            raise ValueError("discovery interpretation must not be empty")

    def _exists(self, entity: str) -> bool:
        if entity in {"player", *self.state.world.rooms, *self.state.world.items, *self.state.world.npcs}:
            return True
        return bool(self.state.world_facts.query("item_name", entity, None)) or bool(
            self.state.world_facts.query("npc_name", entity, None)
        )

    def _location(self, entity: str) -> str:
        holding = self.state.world_facts.query("holding", None, entity)
        if holding:
            return self._actor_location(holding[0][1])
        room_item = self.state.world_facts.query("room_item", None, entity)
        if room_item:
            return room_item[0][1]
        npc_at = self.state.world_facts.query("npc_at", entity, None)
        if npc_at:
            return npc_at[0][2]
        if entity in self.state.world.rooms:
            return entity
        if entity == "player":
            return player_location(self.state)
        return ""

    def _actor_location(self, actor: str) -> str:
        if actor == "player":
            return player_location(self.state)
        facts = self.state.world_facts.query("npc_at", actor, None)
        return facts[0][2] if facts else ""

    def _perceptible(self, observer: str, entity: str, location: str) -> bool:
        concealed = self.state.world_facts.holds("concealed", entity, location)
        exposed = self.state.world_facts.holds("exposed", entity, location)
        if concealed and not exposed:
            return False
        light = self.state.world_facts.query("light", location, None)
        if light and light[0][2].strip().lower() in {"dark", "blackout", "none"}:
            return self.state.world_facts.holds("sensory", observer, "dark_vision")
        blocked = self.state.world_facts.holds("sensory_blocked", location, entity)
        return not blocked


def observer_context_slice(state, observer: str) -> tuple[tuple[str, ...], ...]:
    """Return canonical facts safe to provide to one observer."""
    resolver = ObservationResolver(state)
    permitted: list[tuple[str, ...]] = []
    for fact in state.world_facts.all():
        if not fact:
            continue
        if fact[0] in {"knows", "believes", "suspects", "conceals", "may_infer"}:
            if len(fact) > 1 and fact[1] == observer:
                permitted.append(fact)
            continue
        if fact[0] in {"case_fact", "secret", "villain_motive", "villain_means", "villain_opportunity"}:
            key = fact[1] if len(fact) > 1 else ""
            if state.world_facts.holds("knows", observer, key):
                permitted.append(fact)
            continue
        entities = _fact_entities(fact)
        observer_owned = (
            fact[0] in {"discovery", "interpreted", "recognized"}
            and len(fact) > 1
            and fact[1] == observer
        )
        if not entities or any(resolver.resolve(observer, entity).perceptible for entity in entities) or observer_owned:
            permitted.append(fact)
    return tuple(sorted(permitted))


def speaker_context_slice(state, speaker: str) -> tuple[tuple[str, ...], ...]:
    """Return the addressed NPC's own knowledge plus what is perceptible in scene."""
    visible = set(observer_context_slice(state, speaker))
    for predicate in ("knows", "believes", "suspects", "conceals", "may_infer"):
        for fact in state.world_facts.query(predicate, speaker, None):
            key = fact[2]
            for candidate in state.world_facts.query("case_fact", key, None):
                visible.add(candidate)
    return tuple(sorted(visible))


def _fact_entities(fact: tuple[str, ...]) -> tuple[str, ...]:
    if fact[0] in {
        "at", "npc_at", "holding", "room_item", "visible", "observed", "recognized",
        "concealed", "exposed", "accessible",
    }:
        return tuple(term for term in fact[1:] if term not in {"player"})
    if fact[0] in {
        "item_name", "item_kind", "item_description", "item_owner", "item_driver", "item_state",
        "clue_text", "trace", "evidence_state", "evidence_contaminated",
    }:
        return (fact[1],) if len(fact) > 1 else ()
    if fact[0] in {
        "npc_name", "npc_trait", "npc_identity", "npc_appearance", "npc_pronouns", "npc_role",
        "npc_relationship", "npc_scene_purpose",
    }:
        return (fact[1],) if len(fact) > 1 else ()
    if fact[0] in {"room_name", "room_description", "light", "weather", "sensory_blocked"}:
        return (fact[1],) if len(fact) > 1 else ()
    if fact[0] in {"discovery", "interpreted"}:
        return (fact[1],) if len(fact) > 1 else ()
    return ()


def visible_entities(state, observer: str, room_id: str | None = None) -> tuple[str, ...]:
    resolver = ObservationResolver(state)
    room = room_id or resolver._actor_location(observer)
    candidates = tuple(fact[2] for fact in state.world_facts.query("room_item", room, None))
    candidates += tuple(fact[1] for fact in state.world_facts.query("npc_at", None, room))
    return tuple(entity for entity in candidates if resolver.resolve(observer, entity).perceptible)
