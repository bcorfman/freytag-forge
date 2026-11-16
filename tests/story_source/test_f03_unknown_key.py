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


def test_unknown_key_mutation_changes_only_the_reveal(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    before = load_tree(root)
    patch_source(root, "scenes/1A.yaml", "reveals[find_card].done_when", "the card is found")

    assert _changed_paths(before, load_tree(root)) == {"scenes/1A.yaml.reveals.0.done_when"}


def test_unknown_key_diagnostic(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.yaml", "reveals[find_card].done_when", "the card is found")

    diagnostics = story_source.check_source_tree(root)
    assert [diagnostic.name for diagnostic in diagnostics] == ["L1.unknown_key"]
    assert diagnostics[0].file == "scenes/1A.yaml"
    assert diagnostics[0].field == "done_when"
    assert diagnostics[0].address
    assert story_source.check_source_tree(copy_fixture("mini_ok", tmp_path / "clean")) == []
