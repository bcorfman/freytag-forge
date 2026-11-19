"""Verify lossless fact and placement conversion from the default package."""

from pathlib import Path

import yaml

from storygame.story_package.loader import load_legacy_story_package
from storygame.story_source.convert_facts import convert_facts

# NOTE: The compiler renames source `delivery.source_entity` to the package's `source_entity_id`.
# NOTE: The compiler routes every non-item placement to character placements; this converter merges the
#       two package maps while preserving order within each routed kind.
# NOTE: The package contains one duplicate legacy `world.facts` id; the source contract requires distinct ids.
# NOTE: Entry facts exist in the package, but `build_facts` generates them before source declarations; declaring
#       them here would duplicate records, so compiler behavior wins and the converter leaves them out.


LEGACY_ROOT = Path("tests/fixtures/parity/continuity-initiative/legacy")


def test_converter_owns_every_distinct_fact_once_and_serializes() -> None:
    """Every source-declared package fact is declared exactly once and remains YAML-safe."""

    package = load_legacy_story_package(LEGACY_ROOT)
    result = convert_facts(package)
    fact_ids = [fact_id for document in result.scene_docs.values() for fact_id in document["facts"]] + list(
        result.unplaced_facts
    )
    entry_ids = {f"scene_{scene.metadata.scene_id.lower()}_entry_known" for scene in package.scenes}
    expected = (set(package.world.facts) | {fact.id for fact in package.knowledge.facts}) - entry_ids

    assert len(fact_ids) == len(set(fact_ids)) == len(expected)
    assert set(fact_ids) == expected
    assert not entry_ids & set(fact_ids)
    assert len(result.unplaced_facts) == 13
    assert set(result.unplaced_facts) == {
        "architects_strategy_known",
        "archive_security_sweep",
        "brandon_prepared_before_event",
        "facility_perimeter_reached",
        "false_identities_ready",
        "identity_scrutiny_visible",
        "inspector_cover_under_review",
        "kristin_deliberately_left_behind",
        "national_detention_network_known",
        "prisoner_records_corrupted",
        "processing_numbers_used_in_confrontation",
        "purge_transfers_underway",
        "service_route_used_in_confrontation",
    }
    for scene in package.scenes:
        entry_id = f"scene_{scene.metadata.scene_id.lower()}_entry_known"
        entry = next(fact for fact in package.knowledge.facts if fact.id == entry_id)
        assert entry.purpose == f"The safe opening frame for scene {scene.metadata.scene_id} has been established."
    assert all(list(document) == ["facts", "placements"] for document in result.scene_docs.values())
    yaml.safe_dump({"scenes": result.scene_docs, "unplaced_facts": result.unplaced_facts})


def test_fact_declarations_copy_purposes_effects_and_delivery_fields() -> None:
    """Spot-check three fact records against their immutable package models."""

    package = load_legacy_story_package(LEGACY_ROOT)
    result = convert_facts(package)
    declarations = {
        fact_id: declaration
        for document in result.scene_docs.values()
        for fact_id, declaration in document["facts"].items()
    } | result.unplaced_facts

    for fact_id in ("memory_card_recovered", "continuity_initiative_known", "facility_perimeter_reached"):
        fact = next(item for item in package.knowledge.facts if item.id == fact_id)
        assert declarations[fact_id]["purpose"] == fact.purpose

    effects = package.world.fact_effects["memory_card_recovered"]
    assert declarations["memory_card_recovered"]["on_assert"] == [
        effect.model_dump(by_alias=True, exclude_none=True, exclude_defaults=True, mode="python") for effect in effects
    ]
    delivery = next(item for item in package.deliveries if item.fact_id == "continuity_initiative_known")
    assert declarations["continuity_initiative_known"]["delivery"]["fallback_text"] == delivery.fallback_text
    assert declarations["continuity_initiative_known"]["delivery"]["source_kind"] == delivery.source_kind


def test_placement_routing_copies_three_package_records() -> None:
    """Item and non-item placements are emitted as plain source values."""

    package = load_legacy_story_package(LEGACY_ROOT)
    result = convert_facts(package)
    placements = result.scene_docs["1A"]["placements"]
    scene = next(item for item in package.scenes if item.metadata.scene_id == "1A")

    for entity_id in ("memory_card", "michelle_phone", "kristin"):
        source = scene.metadata.item_placements.get(entity_id, scene.metadata.character_placements.get(entity_id))
        expected = (
            source
            if isinstance(source, str)
            else source.model_dump(by_alias=True, exclude_none=True, exclude_defaults=True, mode="python")
        )
        assert placements[entity_id] == expected


def test_fact_set_in_two_scenes_is_declared_in_first_scene() -> None:
    """A repeated setter follows story order, as required by layer two."""

    package = load_legacy_story_package(LEGACY_ROOT)
    result = convert_facts(package)
    route_scenes = [
        route.scene_id
        for route in package.storylet_routes.storylets
        for realization in route.realizations
        for operation in realization.operations
        if operation.fact_id == "trust_brandon"
    ]
    scene_order = [scene.metadata.scene_id for scene in package.scenes]
    assert len(set(route_scenes)) >= 2
    owner = next(scene_id for scene_id, document in result.scene_docs.items() if "trust_brandon" in document["facts"])
    assert owner == min(set(route_scenes), key=scene_order.index)
