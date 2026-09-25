"""Conversion of authored world data to the worldkeeper schema."""

from storygame.story_package.models import WorldSource


def world_source_schema_data(world: WorldSource) -> dict:
    entities = []
    kinds = [kind.model_dump() if hasattr(kind, "model_dump") else kind for kind in world.kinds]
    for entity in world.locations:
        entities.append(
            {
                "id": entity.id,
                "name": entity.name,
                "aliases": list(entity.aliases),
                "kind": "area",
                "parent": entity.parent,
            }
        )
    for entity in world.npcs:
        entities.append({"id": entity.id, "name": entity.name, "aliases": list(entity.aliases), "kind": "character"})
    for item in world.items:
        entities.append(
            {
                "id": item.id,
                "name": item.name,
                "aliases": list(item.aliases),
                "kind": item.kind,
                "fixed": item.fixed,
                "openable": item.openable,
                "open": item.open,
                "hidden": item.hidden,
                "contents": list(item.contents),
                "owner": item.owner,
            }
        )
    return {"kinds": kinds, "entities": entities}
