from __future__ import annotations

import copy
from pathlib import Path

from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source


def test_leak_null_vs_empty_fixture_changes_only_one_match_entry(tmp_path: Path) -> None:
    baseline = load_tree(copy_fixture("mini_ok", tmp_path / "baseline"))
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(root, "scenes/2C.match.yaml", "claims.k_scene_2c_entry.leak_terms", [])

    expected = copy.deepcopy(baseline)
    expected["scenes/2C.match.yaml"]["claims"]["k_scene_2c_entry"]["leak_terms"] = []  # type: ignore[index]
    assert load_tree(root) == expected


def test_leak_null_and_empty_compile_differently(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean) == []
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(root, "scenes/2C.match.yaml", "claims.k_scene_2c_entry.leak_terms", [])
    package = story_source.compile_source_tree(root)

    by_id = {item.id: item for item in package.knowledge.knowledge}
    assert by_id["k_scene_1a_entry"].leak_terms is None
    assert by_id["k_scene_2c_entry"].leak_terms == ()
    leak_owners = {owner for owners in package.knowledge_indexes.leak_term_to_knowledge.values() for owner in owners}
    assert "k_scene_1a_entry" in leak_owners
    assert "k_scene_2c_entry" not in leak_owners
