"""Pure resolution of package-declared world connections."""

import re
from dataclasses import dataclass

from worldkeeper import World

from storygame.runtime.facts import FactStore
from storygame.story_package.models import Connection, StoryPackage


@dataclass(frozen=True)
class TraversalResolution:
    connection: Connection | None
    refusal_reason: str | None


def _fact_true(facts: FactStore, fact_id: str) -> bool:
    return any(fact.value == "true" for fact in facts.matching(fact_id, "story"))


_MOVEMENT_VERBS = frozenset({"go", "walk", "head", "travel", "move", "take", "follow", "enter", "exit", "return"})


def _words(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.casefold()))


def _phrase_present(command_words: tuple[str, ...], phrase: str) -> bool:
    target = _words(phrase.replace("_", " "))
    return bool(target) and any(
        command_words[index : index + len(target)] == target for index in range(len(command_words))
    )


def _entity_terms(entity) -> tuple[str, ...]:
    return (entity.id, entity.name, *entity.aliases)


def match_traversal_command(package: StoryPackage, facts: FactStore, world: World, command: str) -> str | None:
    """Match an imperative movement command to one unambiguous outgoing route."""

    words = _words(command)
    if not words or words[0] not in _MOVEMENT_VERBS:
        return None
    current_place = world.parent(package.world.protagonist_id)
    if current_place is None:
        return None
    routes = tuple(
        connection for connection in package.connections if world.contains(connection.from_place_id, current_place)
    )
    if not routes:
        return None
    entities = {
        entity.id: entity
        for group in (package.world.locations, package.world.npcs, package.world.items, package.world.groups)
        for entity in group
    }
    candidates = []
    for connection in routes:
        destination = entities[connection.to_place_id]
        destination_named = any(_phrase_present(words[1:], term) for term in _entity_terms(destination))
        via = entities.get(connection.via_id) if connection.via_id else None
        via_named = via is not None and any(_phrase_present(words[1:], term) for term in _entity_terms(via))
        named_entity_ids = {
            entity_id
            for entity_id, entity in entities.items()
            if any(_phrase_present(words[1:], term) for term in _entity_terms(entity))
        }
        allowed_entity_ids = {connection.to_place_id, connection.via_id}
        if (destination_named or via_named) and not (named_entity_ids - allowed_entity_ids):
            candidates.append(connection)
    return candidates[0].to_place_id if len(candidates) == 1 else None


def resolve_traversal(
    package: StoryPackage, facts: FactStore, world: World, destination_id: str
) -> TraversalResolution:
    """Resolve one destination without changing facts or the world."""

    current_place = world.parent(package.world.protagonist_id)
    if current_place is None:
        return TraversalResolution(None, "no_route")
    if world.contains(destination_id, current_place):
        return TraversalResolution(None, "already_there")
    routes = tuple(
        connection
        for connection in package.connections
        if connection.to_place_id == destination_id and world.contains(connection.from_place_id, current_place)
    )
    if not routes:
        return TraversalResolution(None, "no_route")
    for connection in routes:
        if connection.access_fact_id is None or _fact_true(facts, connection.access_fact_id):
            return TraversalResolution(connection, None)
    return TraversalResolution(routes[0], "access_closed")
