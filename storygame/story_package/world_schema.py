"""Conversion of authored world data to the worldkeeper schema."""

from storygame.story_package.models import WorldSource


def world_source_schema_data(world: WorldSource) -> dict:
    entities = []
    for entity in world.locations:
        entities.append({"id": entity.id, "name": entity.name, "aliases": list(entity.aliases), "kind": "area"})
    for entity in world.npcs:
        entities.append({"id": entity.id, "name": entity.name, "aliases": list(entity.aliases), "kind": "character"})
    for item in world.items:
        entities.append(
            {
                "id": item.id,
                "name": item.name,
                "aliases": list(item.aliases),
                "kind": "thing",
                "fixed": item.fixed,
            }
        )
    return {"entities": entities}
