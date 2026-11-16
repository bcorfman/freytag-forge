from __future__ import annotations

from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree, patch_source


def _changed_paths(before: dict[str, object], after: dict[str, object]) -> set[str]:
    changed: set[str] = set()

    def visit(left: object, right: object, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                child = f"{path}.{key}" if path else str(key)
                if key not in left or key not in right:
                    changed.add(child)
                else:
                    visit(left[key], right[key], child)
        elif isinstance(left, list) and isinstance(right, list):
            for index in range(max(len(left), len(right))):
                child = f"{path}.{index}"
                if index >= len(left) or index >= len(right):
                    changed.add(child)
                else:
                    visit(left[index], right[index], child)
        elif left != right:
            changed.add(path)

    for name in sorted(set(before) | set(after)):
        if name not in before or name not in after:
            changed.add(name)
        else:
            visit(before[name], after[name], name)
    return changed


def test_fact_two_owners_mutation_changes_only_scene_2c(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    before = load_tree(root)
    fact = before["scenes/1A.yaml"]["facts"]["memory_card_recovered"]
    patch_source(root, "scenes/2C.yaml", "facts.memory_card_recovered", fact)

    assert _changed_paths(before, load_tree(root)) == {"scenes/2C.yaml.facts.memory_card_recovered"}


def test_fact_two_owners_diagnostic(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    root = copy_fixture("mini_ok", tmp_path)
    tree = load_tree(root)
    patch_source(
        root,
        "scenes/2C.yaml",
        "facts.memory_card_recovered",
        tree["scenes/1A.yaml"]["facts"]["memory_card_recovered"],
    )

    diagnostics = story_source.check_source_tree(root)
    assert [diagnostic.name for diagnostic in diagnostics] == ["L2.fact_one_owner"]
    assert diagnostics[0].file
    assert diagnostics[0].address
    assert diagnostics[0].field
    assert story_source.check_source_tree(copy_fixture("mini_ok", tmp_path / "clean")) == []
