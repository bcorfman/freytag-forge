# NOTE: F08 settles condition-fact misses as L2.dangling_ref; this assumes effect-fact misses use L2.undeclared_fact.
"""Focused mutation tests for story-source layer-two fact/reference checks."""

from pathlib import Path

from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source


def _names(story_source: object, root: Path) -> list[str]:
    """Return diagnostic names through the deliberately small source proxy."""

    return [diagnostic.name for diagnostic in story_source.check_source_tree(root)]


def _assert_clean(story_source: object, tmp_path: Path) -> None:
    """Ensure the base fixture remains free of layer-two diagnostics."""

    assert story_source.check_source_tree(copy_fixture("mini_ok", tmp_path / "clean")) == []


def test_duplicate_id_diagnostic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/2C.yaml", "reveals[michelle_changes_the_choice].storylet_id", "SL-1A-E")

    diagnostics = story_source.check_source_tree(root)
    assert _names(story_source, root) == ["L2.duplicate_id"]
    diagnostic = diagnostics[0]
    assert diagnostic.file == "scenes/2C.yaml"
    assert diagnostic.address and diagnostic.field
    assert "SL-1A-E" in diagnostic.message
    _assert_clean(story_source, tmp_path)


def test_dangling_reference_diagnostic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0.use", "missing_shared")

    diagnostics = story_source.check_source_tree(root)
    assert _names(story_source, root) == ["L2.dangling_ref"]
    diagnostic = diagnostics[0]
    assert diagnostic.file == "scenes/1A.match.yaml"
    assert diagnostic.address and diagnostic.field
    assert "missing_shared" in diagnostic.message
    _assert_clean(story_source, tmp_path)


def test_fact_one_owner_diagnostic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    tree = load_tree(root)
    patch_source(
        root,
        "scenes/2C.yaml",
        "facts.memory_card_recovered",
        tree["scenes/1A.yaml"]["facts"]["memory_card_recovered"],
    )

    diagnostics = story_source.check_source_tree(root)
    assert _names(story_source, root) == ["L2.fact_one_owner"]
    diagnostic = diagnostics[0]
    assert diagnostic.file == "scenes/2C.yaml"
    assert diagnostic.address and diagnostic.field
    assert "memory_card_recovered" in diagnostic.message
    _assert_clean(story_source, tmp_path)


def test_fact_declaring_scene_diagnostic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    tree = load_tree(root)
    fact = tree["scenes/1A.yaml"]["facts"]["memory_card_recovered"]
    patch_source(root, "scenes/2C.yaml", "facts.memory_card_recovered", fact)
    patch_source(root, "scenes/1A.yaml", "facts.memory_card_recovered")

    diagnostics = story_source.check_source_tree(root)
    assert _names(story_source, root) == ["L2.fact_declaring_scene"]
    diagnostic = diagnostics[0]
    assert diagnostic.file == "scenes/2C.yaml"
    assert diagnostic.address and diagnostic.field
    assert "memory_card_recovered" in diagnostic.message
    assert "scenes/1A.yaml" in diagnostic.message
    _assert_clean(story_source, tmp_path)


def test_unplaced_fact_diagnostic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "catalog.yaml", "unplaced_facts", {"orphan_fact": {"purpose": "An orphan fact."}})
    tree = load_tree(root)
    sets = dict(tree["scenes/1A.yaml"]["beats"][0]["sets"])
    sets["orphan_fact"] = True
    patch_source(root, "scenes/1A.yaml", "beats[0].sets", sets)

    diagnostics = story_source.check_source_tree(root)
    assert _names(story_source, root) == ["L2.unplaced_fact"]
    diagnostic = diagnostics[0]
    assert diagnostic.file == "catalog.yaml"
    assert diagnostic.address and diagnostic.field
    assert "orphan_fact" in diagnostic.message
    _assert_clean(story_source, tmp_path)


def test_undeclared_fact_diagnostic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    tree = load_tree(root)
    sets = dict(tree["scenes/1A.yaml"]["beats"][0]["sets"])
    sets["missing_fact"] = True
    patch_source(root, "scenes/1A.yaml", "beats[0].sets", sets)

    diagnostics = story_source.check_source_tree(root)
    assert _names(story_source, root) == ["L2.undeclared_fact"]
    diagnostic = diagnostics[0]
    assert diagnostic.file == "scenes/1A.yaml"
    assert diagnostic.address and diagnostic.field
    assert "missing_fact" in diagnostic.message
    _assert_clean(story_source, tmp_path)
