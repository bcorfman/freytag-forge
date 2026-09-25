"""Conversion of authored world data to the worldkeeper schema."""

from storygame.story_package.models import WorldSource


def world_source_schema_data(world: WorldSource) -> dict:
    entities = []
    kinds = [{"id": kind.id, "is": list(kind.is_)} for kind in world.kinds]
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
        item_data = {
            "id": item.id,
            "name": item.name,
            "aliases": list(item.aliases),
            "kind": item.kind,
            "openable": item.openable,
            "open": item.open,
            "hidden": item.hidden,
            "contents": list(item.contents),
            "owner": item.owner,
        }
        if item.fixed is not None:
            item_data["fixed"] = item.fixed
        entities.append(item_data)
    return {"kinds": kinds, "entities": entities}
