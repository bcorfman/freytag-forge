from __future__ import annotations

from pathlib import Path

from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source


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


def test_dangling_mutations_change_only_the_four_named_references(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    before = load_tree(root)
    patch_source(
        root,
        "scenes/1A.yaml",
        "reveals[find_card].variants.quiet.text",
        "{missing} Her laptop is still out in her truck.",
    )
    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0.use", "nope")
    patch_source(
        root,
        "scenes/1A.yaml",
        "reveals[find_card].variants.quiet.when",
        {"patrol_in_house": False, "missing_fact": True},
    )
    patch_source(root, "scenes/1A.yaml", "exit.to", "ZZ")

    assert _changed_paths(before, load_tree(root)) == {
        "scenes/1A.match.yaml.claims.k_sl_1a_b_r0.use",
        "scenes/1A.yaml.exit.to",
        "scenes/1A.yaml.reveals.0.variants.quiet.text",
        "scenes/1A.yaml.reveals.0.variants.quiet.when.missing_fact",
    }


def test_dangling_diagnostics(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(
        root,
        "scenes/1A.yaml",
        "reveals[find_card].variants.quiet.text",
        "{missing} Her laptop is still out in her truck.",
    )
    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0.use", "nope")
    patch_source(
        root,
        "scenes/1A.yaml",
        "reveals[find_card].variants.quiet.when",
        {"patrol_in_house": False, "missing_fact": True},
    )
    patch_source(root, "scenes/1A.yaml", "exit.to", "ZZ")

    diagnostics = story_source.check_source_tree(root)
    assert sorted(diagnostic.name for diagnostic in diagnostics) == [
        "L2.dangling_ref",
        "L2.dangling_ref",
        "L2.dangling_ref",
        "L2.dangling_ref",
    ]
    for diagnostic in diagnostics:
        assert diagnostic.file
        assert diagnostic.address
        assert diagnostic.field
    assert story_source.check_source_tree(copy_fixture("mini_ok", tmp_path / "clean")) == []
