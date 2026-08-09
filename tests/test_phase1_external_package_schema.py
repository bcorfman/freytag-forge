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


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda package: package["map"]["paths"].append(
                {"direction": "north", "from": "missing", "to": "camp"}
            ),
            "unknown map room",
        ),
        (
            lambda package: package["items"][0].update(
                {"initial_custody": {"kind": "npc", "id": "missing"}}
            ),
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
