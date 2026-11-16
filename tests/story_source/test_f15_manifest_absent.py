from __future__ import annotations

from pathlib import Path

from tests.story_source.helpers import copy_fixture, load_tree, require_story_source


def test_manifest_absent_fixture_keeps_the_source_tree_unchanged(tmp_path: Path) -> None:
    baseline = load_tree(copy_fixture("mini_ok", tmp_path / "baseline"))
    root = copy_fixture("mini_ok", tmp_path / "mutated")

    assert "ownership.yaml" not in load_tree(root)
    assert load_tree(root) == baseline


def test_manifest_absent_compiles_without_ownership_diagnostics(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    assert story_source.check_source_tree(root) == []
    package = story_source.compile_source_tree(root)

    # The parity assertion belongs here once the legacy loader for
    # data/stories/continuity-initiative is paired with this source slice.
    assert package.storylet_routes.canonical_scene_chain == ("1A", "2C")
