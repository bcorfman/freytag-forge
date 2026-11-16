from __future__ import annotations

from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree, patch_source

_NEEDS = [
    {"item": "memory_card", "relation": "exists"},
    {"item": "michelle_phone", "relation": "held"},
    {"item": "michelle_drawer", "relation": "reach"},
    {"item": "back_door", "relation": "exists", "not": True},
]


def test_typed_needs_change_only_the_exit_needs(tmp_path: Path) -> None:
    baseline = copy_fixture("mini_ok", tmp_path / "baseline")
    root = copy_fixture("mini_ok", tmp_path / "changed")
    patch_source(root, "scenes/1A.yaml", "exit.needs", _NEEDS)

    baseline_tree = load_tree(baseline)
    changed_tree = load_tree(root)
    assert set(changed_tree) == set(baseline_tree)
    changed_scene = dict(changed_tree["scenes/1A.yaml"])
    baseline_scene = dict(baseline_tree["scenes/1A.yaml"])
    changed_exit = dict(changed_scene["exit"])
    baseline_exit = dict(baseline_scene["exit"])
    assert changed_exit.pop("needs") == _NEEDS
    assert changed_exit == {key: value for key, value in baseline_exit.items() if key != "needs"}
    assert changed_scene["exit"] != baseline_scene["exit"]
    changed_scene["exit"] = baseline_scene["exit"]
    assert changed_scene == baseline_scene
    assert all(changed_tree[path] == baseline_tree[path] for path in baseline_tree if path != "scenes/1A.yaml")


def test_only_exists_and_held_needs_become_required_dependencies(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.yaml", "exit.needs", _NEEDS)
    clean_root = copy_fixture("mini_ok", tmp_path / "clean")

    assert story_source.check_source_tree(root) == []
    assert story_source.check_source_tree(clean_root) == []
    package = story_source.compile_source_tree(root)
    transition = next(item for item in package.pacing.transitions if item.id == "t_1a_1b")
    assert set(transition.required_dependencies) == {"memory_card", "michelle_phone"}
    assert len(transition.required_dependencies) == 2
