"""Build world, catalog, fact, and delivery models from source documents."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from storygame.story_package.models import (
    Connection,
    DisclosureGuard,
    FactDefinition,
    FactDelivery,
    Group,
    Item,
    KindDeclaration,
    Location,
    Npc,
    PropDeclaration,
    WorldEffect,
    WorldSource,
)

from .c_passages import operations


def _records(section: object) -> list[tuple[str, dict[str, Any]]]:
    """Return keyed records with their IDs injected in written order."""

    if not isinstance(section, Mapping):
        return []
    return [(identifier, {"id": identifier, **dict(record)}) for identifier, record in section.items()]


def _records_without_bio(section: object, fact_ids: set[str]) -> list[tuple[str, dict[str, Any]]]:
    """Return character records without the reader-only catalog bio."""

    records = _records(section)
    for _, record in records:
        record.pop("bio", None)
        if record.get("named_by") not in fact_ids:
            record.pop("named_by", None)
            record.pop("unnamed_label", None)
    return records


def build_world(
    story: Mapping[str, Any], catalog: Mapping[str, Any], facts: Sequence[tuple[str, Mapping[str, Any]]]
) -> WorldSource:
    """Create the immutable world source, preserving catalog order."""

    fact_ids = {fact_id for fact_id, _ in facts}
    locations = tuple(Location.model_validate(record) for _, record in _records(catalog.get("places")))
    npcs = tuple(Npc.model_validate(record) for _, record in _records_without_bio(catalog.get("characters"), fact_ids))
    groups = tuple(Group.model_validate(record) for _, record in _records(catalog.get("groups")))
    items = tuple(Item.model_validate(record) for _, record in _records(catalog.get("items")))
    kinds = tuple(KindDeclaration.model_validate(record) for _, record in _records(catalog.get("kinds")))
    props = tuple(PropDeclaration.model_validate(record) for _, record in _records(catalog.get("props")))
    ordered_fact_ids = tuple(fact_id for fact_id, _ in facts)
    effects = {
        fact_id: tuple(WorldEffect.model_validate(effect) for effect in declaration.get("on_assert", ()))
        for fact_id, declaration in facts
        if "on_assert" in declaration
    }
    guards = tuple(_guard(identifier, record) for identifier, record in _records(catalog.get("disclosure_guards")))
    return WorldSource(
        story_id=story["story"],
        protagonist_id=story["protagonist"],
        locations=locations,
        npcs=npcs,
        groups=groups,
        items=items,
        kinds=kinds,
        props=props,
        facts=ordered_fact_ids,
        fact_effects=effects,
        protected_knowledge=tuple(catalog.get("protected_knowledge", ())),
        disclosure_guards=guards,
    )


def _guard(identifier: str, record: Mapping[str, Any]) -> DisclosureGuard:
    """Convert the source spelling of a disclosure guard."""

    data = {"id": identifier, **dict(record)}
    if "unlock_claim" in data:
        data["unlock_knowledge_id"] = data.pop("unlock_claim")
    return DisclosureGuard.model_validate(data)


def build_facts(
    scene_records: Sequence[tuple[str, Mapping[str, Any]]], catalog: Mapping[str, Any]
) -> tuple[tuple[str, Mapping[str, Any]], ...]:
    """Order declared facts by scene, with each generated entry fact first."""

    result: list[tuple[str, Mapping[str, Any]]] = []
    owned: set[str] = set()
    for scene_id, scene in scene_records:
        entry_id = f"scene_{scene_id.lower()}_entry_known"
        result.append((entry_id, {"purpose": f"The safe opening frame for scene {scene_id} has been established."}))
        for fact_id, declaration in (scene.get("facts", {}) or {}).items():
            if fact_id not in owned:
                result.append((fact_id, declaration))
                owned.add(fact_id)
    for fact_id, declaration in (catalog.get("unplaced_facts", {}) or {}).items():
        if fact_id not in owned:
            result.append((fact_id, declaration))
            owned.add(fact_id)
    return tuple(result)


def build_fact_models(facts: Sequence[tuple[str, Mapping[str, Any]]]) -> tuple[FactDefinition, ...]:
    """Create knowledge fact definitions from ordered source declarations."""

    return tuple(FactDefinition(id=fact_id, purpose=declaration["purpose"]) for fact_id, declaration in facts)


def build_deliveries(
    scene_records: Sequence[tuple[str, Mapping[str, Any]]],
    facts: Sequence[tuple[str, Mapping[str, Any]]],
) -> tuple[FactDelivery, ...]:
    """Create deliveries in scene and declaration order."""

    scene_by_fact = {
        fact_id: (scene_id, declaration)
        for scene_id, scene in scene_records
        for fact_id, declaration in scene.get("facts", {}).items()
    }
    deliveries: list[FactDelivery] = []
    for fact_id, declaration in facts:
        delivery = declaration.get("delivery")
        if not isinstance(delivery, Mapping):
            continue
        scene_id, _ = scene_by_fact.get(fact_id, (delivery.get("scene"), declaration))
        data = dict(delivery)
        data["fact_id"] = fact_id
        data["scene_id"] = data.pop("scene", None) or scene_id
        data["must_convey"] = ()
        data["costs"] = operations(delivery.get("costs"))
        deliveries.append(FactDelivery.model_validate(data))
    return tuple(deliveries)


def build_connections(catalog: Mapping[str, Any]) -> tuple[Connection, ...]:
    """Convert catalog connection records in mapping order."""

    result: list[Connection] = []
    for _identifier, record in _records(catalog.get("connections")):
        data = dict(record)
        data["from_place_id"] = data.pop("from")
        data["to_place_id"] = data.pop("to")
        data["via_id"] = data.pop("via", None)
        data["access_fact_id"] = data.pop("access_fact", None)
        data["arrival_text"] = data.pop("arrival")
        data["consequences"] = operations(data.get("consequences"))
        result.append(Connection(**data))
    return tuple(result)
