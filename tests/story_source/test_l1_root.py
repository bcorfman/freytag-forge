"""Tests for root, match, lock, and lexicon layer-one checks."""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.story_source.helpers import copy_fixture, patch_source, require_story_source

# NOTE: The contract does not mark every catalog top-level key R/O; this suite assumes
# the complete catalog table is required when catalog.yaml exists, as in the compiler input.


def _assert_one(diagnostics: list[object], name: str, file: str) -> None:
    matches = [diagnostic for diagnostic in diagnostics if diagnostic.name == name]
    assert matches
    assert all(diagnostic.file == file and diagnostic.address and diagnostic.field for diagnostic in matches)


def test_mini_ok_is_clean(tmp_path: Path) -> None:
    story_source = require_story_source()
    assert story_source.check_source_tree(copy_fixture("mini_ok", tmp_path)) == []


def test_root_unknown_key(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "story.yaml", "unexpected", True)
    diagnostics = story_source.check_source_tree(root)
    _assert_one(diagnostics, "L1.unknown_key", "story.yaml")


def test_root_missing_key(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "story.yaml", "protagonist")
    diagnostics = story_source.check_source_tree(root)
    _assert_one(diagnostics, "L1.missing_key", "story.yaml")


def test_root_type_error(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "story.yaml", "budget_seconds", "long")
    diagnostics = story_source.check_source_tree(root)
    _assert_one(diagnostics, "L1.type", "story.yaml")


def test_root_enum_error(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    (root / "ownership.yaml").write_text("schema: 1\ncatalog: neither\nscenes: {}\n", encoding="utf-8")
    diagnostics = story_source.check_source_tree(root)
    _assert_one(diagnostics, "L1.enum", "ownership.yaml")


def test_root_id_pattern_error(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    document = yaml.safe_load((root / "catalog.yaml").read_text(encoding="utf-8"))
    document["places"]["Not an id"] = document["places"].pop("mcgehee_home")
    (root / "catalog.yaml").write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    diagnostics = story_source.check_source_tree(root)
    _assert_one(diagnostics, "L1.id_pattern", "catalog.yaml")


def test_match_scene_is_checked_against_file_name(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.match.yaml", "scene", "2C")
    diagnostics = story_source.check_source_tree(root)
    _assert_one(diagnostics, "L1.match_scene", "scenes/1A.match.yaml")


def test_lexicon_reference_is_off_by_default(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.match.yaml", "shared.drawer_search.must_convey", [{"from": ["$memory_card"]}])
    diagnostics = story_source.check_source_tree(root)
    _assert_one(diagnostics, "L1.lexicon_off", "scenes/1A.match.yaml")


def test_plural_twin_is_off_by_default(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0.aliases", ["saved file(s)"])
    diagnostics = story_source.check_source_tree(root)
    _assert_one(diagnostics, "L1.plural_off", "scenes/1A.match.yaml")


def test_malformed_lexicon_is_ignored_when_all_matches_are_off(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    for scene in ("1A", "2C"):
        path = root / f"scenes/{scene}.match.yaml"
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        document = {
            "schema": document["schema"],
            "scene": document["scene"],
            "lexicon": False,
            **{key: document[key] for key in document if key not in {"schema", "scene", "lexicon"}},
        }
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    (root / "lexicon.yaml").write_text(
        "schema: 1\nentities: broken\nconcepts: []\nverb_classes: nope\n", encoding="utf-8"
    )
    assert story_source.check_source_tree(root) == []
