from __future__ import annotations

import pytest

from storygame.engine.world_builder import (
    WorldPackageValidationError,
    build_world_package,
    load_story_package_templates,
    validate_world_package,
)


def test_external_templates_declare_all_phase1_sections() -> None:
    templates = load_story_package_templates()
    assert set(templates) >= {"default", "mystery", "fantasy"}
    fantasy = templates["fantasy"]
    assert {
        "map",
        "characters",
        "items",
        "opening_setup",
        "intent_aliases",
        "effect_templates",
    } <= set(fantasy)


def test_external_template_loader_rejects_bad_schema(tmp_path) -> None:
    bad = tmp_path / "story_packages.yaml"
    bad.write_text("schema_version: 99\npackages: {}\n", encoding="utf-8")
    with pytest.raises(WorldPackageValidationError, match="unsupported schema"):
        load_story_package_templates(bad)


def test_world_package_expands_and_validates_phase1_sections() -> None:
    package = build_world_package("fantasy", "short", 33, "epic")

    assert validate_world_package(package) is package
    assert package["map"]["room_presentation"]
    assert package["characters"]
    assert package["items"]
    assert package["opening_setup"]["public_briefing"]
    assert package["opening_setup"]["protected_knowledge"]
    assert package["intent_aliases"]
    assert package["effect_templates"]
    assert package["map"]["environment"]


def test_world_package_rejects_fragile_items_staged_in_exposed_rooms() -> None:
    package = build_world_package("fantasy", "short", 33, "epic")
    item = package["items"][0]
    item["fragility"] = "weather_sensitive"
    item["initial_custody"] = {"kind": "room", "id": "village_gate"}
    package["map"]["environment"]["village_gate"]["exposure"] = "outdoor"

    with pytest.raises(WorldPackageValidationError, match="fragile item.*exposed room"):
        validate_world_package(package)


def test_world_package_rejects_wind_vulnerable_documents_left_outdoors() -> None:
    package = build_world_package("mystery", "short", 33, "mysterious")
    case_file = next(item for item in package["items"] if item["id"] == "case_file")
    case_file["initial_custody"] = {"kind": "room", "id": "front_steps"}

    with pytest.raises(WorldPackageValidationError, match="wind-vulnerable item.*exposed room"):
        validate_world_package(package)


def test_world_package_allows_a_protected_wind_vulnerable_item_outdoors() -> None:
    package = build_world_package("mystery", "short", 33, "mysterious")
    case_file = next(item for item in package["items"] if item["id"] == "case_file")
    case_file["initial_custody"] = {"kind": "room", "id": "front_steps"}
    case_file["placement_security"] = "protected"

    assert validate_world_package(package) is package


def test_world_package_requires_a_readable_document_to_reveal_new_opening_knowledge() -> None:
    package = build_world_package("mystery", "short", 33, "mysterious")
    case_file = next(item for item in package["items"] if item["id"] == "case_file")
    case_file["readable"]["knowledge"] = ["victim_name", "victim_timeline"]
    case_file["readable"]["npc_disclosures"] = {}

    with pytest.raises(WorldPackageValidationError, match="fact not granted by the opening briefing"):
        validate_world_package(package)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda package: next(item for item in package["items"] if item["id"] == "case_file")["readable"].update(
                {"npc_disclosures": {"missing_npc": ["ledger_entry_time"]}}
            ),
            "unknown NPC",
        ),
        (
            lambda package: (
                next(item for item in package["items"] if item["id"] == "case_file")["readable"].update(
                    {"knowledge": ["ledger_entry_time", "missing_fact"]}
                ),
                next(item for item in package["items"] if item["id"] == "case_file")["readable"].update(
                    {"npc_disclosures": {"daria_stone": ["missing_fact"]}}
                ),
            ),
            "canonical case_fact",
        ),
        (
            lambda package: next(
                character for character in package["characters"] if character["id"] == "daria_stone"
            ).update({"initial_knowledge": ["opening_situation"]}),
            "must be known by NPC",
        ),
        (
            lambda package: package["opening_setup"].update(
                {"public_briefing": [*package["opening_setup"]["public_briefing"], "ledger_entry_time"]}
            ),
            "must not be public",
        ),
    ],
)
def test_world_package_validates_document_npc_disclosures(change, message) -> None:
    package = build_world_package("mystery", "short", 33, "mysterious")
    change(package)

    with pytest.raises(WorldPackageValidationError, match=message):
        validate_world_package(package)


def test_fantasy_package_declares_a_document_npc_disclosure_path() -> None:
    package = build_world_package("fantasy", "short", 33, "epic")
    scroll = next(item for item in package["items"] if item["id"] == "warded_scroll")

    assert scroll["readable"]["npc_disclosures"] == {"selene_ward": ["warded_route"]}
    assert package["opening_setup"]["case_facts"]["warded_route"]
    assert next(character for character in package["characters"] if character["id"] == "selene_ward")[
        "initial_knowledge"
    ] == ["public_briefing", "warded_route"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda package: package["map"]["paths"].append({"direction": "north", "from": "missing", "to": "camp"}),
            "unknown map room",
        ),
        (
            lambda package: package["items"][0].update({"initial_custody": {"kind": "npc", "id": "missing"}}),
            "unknown custody",
        ),
        (
            lambda package: package["opening_setup"].update(
                {"public_briefing": ["secret"], "protected_knowledge": ["secret"]}
            ),
            "protected knowledge",
        ),
        (
            lambda package: package["items"][0].update({"document_visibility": "unknown"}),
            "document visibility",
        ),
    ],
)
def test_world_package_validation_rejects_cross_section_errors(change, message) -> None:
    package = build_world_package("fantasy", "short", 33, "epic")
    change(package)

    with pytest.raises(WorldPackageValidationError, match=message):
        validate_world_package(package)


def test_world_package_validation_rejects_shapes_and_character_contracts() -> None:
    package = build_world_package("fantasy", "short", 33, "epic")
    with pytest.raises(WorldPackageValidationError, match="missing package sections"):
        validate_world_package({})
    with pytest.raises(WorldPackageValidationError, match="invalid shapes"):
        validate_world_package({**package, "map": []})

    package["characters"][0]["location"] = "unknown"
    with pytest.raises(WorldPackageValidationError, match="unknown character location"):
        validate_world_package(package)

    package = build_world_package("fantasy", "short", 33, "epic")
    package["characters"][0]["role"] = ""
    with pytest.raises(WorldPackageValidationError, match="require role"):
        validate_world_package(package)

    package = build_world_package("fantasy", "short", 33, "epic")
    package["items"] = ["not a mapping"]
    with pytest.raises(WorldPackageValidationError, match="items require unique"):
        validate_world_package(package)

    package = build_world_package("fantasy", "short", 33, "epic")
    package["opening_setup"] = []
    with pytest.raises(WorldPackageValidationError, match="opening_setup"):
        validate_world_package(package)

    package = build_world_package("fantasy", "short", 33, "epic")
    package["intent_aliases"] = []
    with pytest.raises(WorldPackageValidationError, match="aliases"):
        validate_world_package(package)
