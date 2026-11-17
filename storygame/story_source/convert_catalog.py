"""Convert loaded package identity and world records to source-tree documents."""

from __future__ import annotations

from typing import Any

from storygame.story_package.models import Connection, DisclosureGuard, StoryPackage


def _record_fields(record: Any) -> dict[str, Any]:
    """Return source-shaped JSON values for a model record without its map ID."""

    fields = record.model_dump(mode="json", by_alias=True, exclude_defaults=True)
    fields.pop("id", None)
    return fields


def _entity_map(records: tuple[Any, ...]) -> dict[str, dict[str, Any]]:
    """Convert ordered model records to an ordered ID-keyed map."""

    return {record.id: _record_fields(record) for record in records}


def _connection_fields(connection: Connection) -> dict[str, Any]:
    """Convert a runtime connection back to the catalog connection spelling."""

    fields = _record_fields(connection)
    converted = {"from": fields.pop("from_place_id"), "to": fields.pop("to_place_id")}
    for runtime_name, source_name in (("via_id", "via"), ("access_fact_id", "access_fact")):
        if runtime_name in fields:
            converted[source_name] = fields.pop(runtime_name)
    consequences = {
        operation.fact_id: "retract" if operation.op == "retract" else operation.value
        for operation in connection.consequences
    }
    if consequences:
        converted["consequences"] = consequences
    converted["arrival"] = fields.pop("arrival_text")
    return converted


def _guard_fields(guard: DisclosureGuard) -> dict[str, Any]:
    """Convert a runtime disclosure guard to the compiler's source spelling."""

    fields = _record_fields(guard)
    if "unlock_knowledge_id" in fields:
        fields["unlock_claim"] = fields.pop("unlock_knowledge_id")
    return fields


def convert_story(package: StoryPackage) -> dict[str, Any]:
    """Return the runtime-backed, reader-free contents of ``story.yaml``."""

    return {
        "schema": 1,
        "story": package.story_id,
        "genre": package.genre,
        "protagonist": package.protagonist_id,
        "budget_seconds": package.pacing.budget_seconds,
        "scenes": list(package.storylet_routes.canonical_scene_chain),
        "principal_characters": [character.id for character in package.characters],
        "retired_ids": {},
    }


def convert_catalog(package: StoryPackage, unplaced_facts: dict[str, Any]) -> dict[str, Any]:
    """Return the runtime-backed contents of ``catalog.yaml`` in package order."""

    world = package.world
    return {
        "schema": 1,
        "places": _entity_map(world.locations),
        "characters": _entity_map(world.npcs),
        "groups": _entity_map(world.groups),
        "items": _entity_map(world.items),
        "kinds": _entity_map(world.kinds),
        "props": _entity_map(world.props),
        "connections": {connection.id: _connection_fields(connection) for connection in package.connections},
        "protected_knowledge": list(world.protected_knowledge),
        "disclosure_guards": {guard.id: _guard_fields(guard) for guard in world.disclosure_guards},
        "unplaced_facts": unplaced_facts,
    }
