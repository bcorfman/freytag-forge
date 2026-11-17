"""Verify package-to-catalog conversion preserves all owned runtime records."""

from pathlib import Path
from typing import Any

from storygame.story_package.loader import load_legacy_story_package
from storygame.story_source.convert_catalog import convert_catalog, convert_story

LEGACY_ROOT = Path("tests/fixtures/parity/continuity-initiative/legacy")


def _package() -> Any:
    return load_legacy_story_package(LEGACY_ROOT)


def _model_fields(record: Any) -> dict[str, Any]:
    fields = record.model_dump(mode="json", by_alias=True, exclude_defaults=True)
    fields.pop("id", None)
    return fields


def _connection_fields(record: Any) -> dict[str, Any]:
    fields = _model_fields(record)
    converted = {"from": fields.pop("from_place_id"), "to": fields.pop("to_place_id")}
    for runtime_name, source_name in (("via_id", "via"), ("access_fact_id", "access_fact")):
        if runtime_name in fields:
            converted[source_name] = fields.pop(runtime_name)
    consequences = {
        operation.fact_id: "retract" if operation.op == "retract" else operation.value
        for operation in record.consequences
    }
    if consequences:
        converted["consequences"] = consequences
    converted["arrival"] = fields.pop("arrival_text")
    return converted


def _guard_fields(record: Any) -> dict[str, Any]:
    fields = _model_fields(record)
    if "unlock_knowledge_id" in fields:
        fields["unlock_claim"] = fields.pop("unlock_knowledge_id")
    return fields


def test_convert_story_uses_runtime_identity_and_canonical_order() -> None:
    package = _package()

    converted = convert_story(package)

    assert list(converted) == [
        "schema",
        "story",
        "genre",
        "protagonist",
        "budget_seconds",
        "scenes",
        "principal_characters",
        "retired_ids",
    ]
    assert converted == {
        "schema": 1,
        "story": package.story_id,
        "genre": package.genre,
        "protagonist": package.protagonist_id,
        "budget_seconds": package.pacing.budget_seconds,
        "scenes": list(package.storylet_routes.canonical_scene_chain),
        "principal_characters": [character.id for character in package.characters],
        "retired_ids": {},
    }


def test_convert_catalog_preserves_order_ids_and_fields() -> None:
    package = _package()
    unplaced = {"unused_fact": {"purpose": "A fact supplied by the caller."}}

    converted = convert_catalog(package, unplaced)

    assert list(converted) == [
        "schema",
        "places",
        "characters",
        "groups",
        "items",
        "kinds",
        "props",
        "connections",
        "protected_knowledge",
        "disclosure_guards",
        "unplaced_facts",
    ]
    assert converted["unplaced_facts"] is unplaced
    sections = {
        "places": package.world.locations,
        "characters": package.world.npcs,
        "groups": package.world.groups,
        "items": package.world.items,
        "kinds": package.world.kinds,
        "props": package.world.props,
    }
    for section, records in sections.items():
        assert list(converted[section]) == [record.id for record in records]
        assert len(converted[section]) == len(records)
        for record in records:
            assert converted[section][record.id] == _model_fields(record)
        for record in records[:3]:
            assert converted[section][record.id] == _model_fields(record)

    connections = package.connections
    assert list(converted["connections"]) == [record.id for record in connections]
    assert len(converted["connections"]) == len(connections)
    for record in connections:
        assert converted["connections"][record.id] == _connection_fields(record)
    for record in connections[:3]:
        assert converted["connections"][record.id] == _connection_fields(record)

    guards = package.world.disclosure_guards
    assert list(converted["disclosure_guards"]) == [record.id for record in guards]
    assert len(converted["disclosure_guards"]) == len(guards)
    for record in guards:
        assert converted["disclosure_guards"][record.id] == _guard_fields(record)
    for record in guards[:3]:
        assert converted["disclosure_guards"][record.id] == _guard_fields(record)

    assert converted["protected_knowledge"] == list(package.world.protected_knowledge)
