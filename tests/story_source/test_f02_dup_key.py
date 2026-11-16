from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import copy_fixture, load_tree


def test_duplicate_key_is_the_only_raw_source_mutation(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    baseline = load_tree(root)
    scene = root / "scenes/1A.yaml"
    original = scene.read_text(encoding="utf-8")
    needle = (
        "        intent: Kristin searches beneath the KMS drawer, finds Michelle's hidden "
        "memory card, and keeps it with her."
    )
    duplicate = needle + "\n        intent: duplicate intent"

    assert original.count(needle) == 1
    scene.write_text(original.replace(needle, duplicate), encoding="utf-8")
    assert scene.read_text(encoding="utf-8").splitlines() == (
        original.splitlines()[: original.splitlines().index(needle) + 1]
        + ["        intent: duplicate intent"]
        + original.splitlines()[original.splitlines().index(needle) + 1 :]
    )
    assert set(baseline) == {
        "story.yaml",
        "catalog.yaml",
        "scenes/1A.yaml",
        "scenes/1A.match.yaml",
        "scenes/2C.yaml",
        "scenes/2C.match.yaml",
    }
    with pytest.raises(yaml.YAMLError, match="duplicate key"):
        load_tree(root)


def test_duplicate_key_diagnostic(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    root = copy_fixture("mini_ok", tmp_path)
    scene = root / "scenes/1A.yaml"
    original = scene.read_text(encoding="utf-8")
    needle = (
        "        intent: Kristin searches beneath the KMS drawer, finds Michelle's hidden "
        "memory card, and keeps it with her."
    )
    scene.write_text(original.replace(needle, needle + "\n        intent: duplicate intent"), encoding="utf-8")

    diagnostics = story_source.check_source_tree(root)
    assert [diagnostic.name for diagnostic in diagnostics].count("L1.duplicate_key") == 1
    for diagnostic in diagnostics:
        assert diagnostic.file
        assert diagnostic.address
        assert diagnostic.field
    assert story_source.check_source_tree(copy_fixture("mini_ok", tmp_path / "clean")) == []
