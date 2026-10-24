"""Pure resolution of package-declared world connections."""

from dataclasses import dataclass

from worldkeeper import World

from storygame.runtime.facts import FactStore
from storygame.story_package.models import Connection, StoryPackage


@dataclass(frozen=True)
class TraversalResolution:
    connection: Connection | None
    refusal_reason: str | None


def _contains(world: World, entity_id: str, ancestor_id: str) -> bool:
    current = entity_id
    while current is not None:
        if current == ancestor_id:
            return True
        current = world.parent(current)
    return False


def _fact_true(facts: FactStore, fact_id: str) -> bool:
    return any(fact.value == "true" for fact in facts.matching(fact_id, "story"))


def resolve_traversal(
    package: StoryPackage, facts: FactStore, world: World, destination_id: str
) -> TraversalResolution:
    """Resolve one destination without changing facts or the world."""

    current_place = world.parent(package.world.protagonist_id)
    if current_place is None:
        return TraversalResolution(None, "no_route")
    if _contains(world, current_place, destination_id):
        return TraversalResolution(None, "already_there")
    routes = tuple(
        connection
        for connection in package.connections
        if connection.to_place_id == destination_id and _contains(world, current_place, connection.from_place_id)
    )
    if not routes:
        return TraversalResolution(None, "no_route")
    for connection in routes:
        if connection.access_fact_id is None or _fact_true(facts, connection.access_fact_id):
            return TraversalResolution(connection, None)
    return TraversalResolution(routes[0], "access_closed")
