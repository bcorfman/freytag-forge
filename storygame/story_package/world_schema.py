"""Conversion of authored world data to the worldkeeper schema."""

from storygame.story_package.models import WorldSource


def world_source_schema_data(world: WorldSource) -> dict:
    entities = []
    kinds = [
        {
            "id": kind.id,
            "is": list(kind.is_),
            "enterable": kind.enterable,
            **({"fixed": kind.fixed} if kind.fixed is not None else {}),
        }
        for kind in world.kinds
    ]
    for entity in world.locations:
        entities.append(
            {
                "id": entity.id,
                "name": entity.name,
                "aliases": list(entity.aliases),
                "kind": "area",
                "parent": entity.parent,
                "owner": entity.owner,
            }
        )
    for entity in world.npcs:
        entities.append({"id": entity.id, "name": entity.name, "aliases": list(entity.aliases), "kind": "character"})
    for entity in world.groups:
        entities.append({"id": entity.id, "name": entity.name, "aliases": list(entity.aliases), "kind": "group"})
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
        if item.enterable is not None:
            item_data["enterable"] = item.enterable
        if item.enter_pole is not None:
            item_data["enter_pole"] = item.enter_pole
        if item.seat_for is not None:
            item_data["seat_for"] = item.seat_for
        if item.axes:
            item_data["axes"] = [
                {
                    "poles": list(axis),
                    "aliases": {alias: pole for pole, aliases in axis.items() for alias in aliases},
                    "initial": next(iter(axis)),
                }
                for axis in item.axes
            ]
        if item.fixed is not None:
            item_data["fixed"] = item.fixed
        entities.append(item_data)
    return {"kinds": kinds, "entities": entities}
