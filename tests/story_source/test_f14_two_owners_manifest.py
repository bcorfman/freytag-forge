from __future__ import annotations

from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree

_OWNERSHIP = """schema: 1
catalog: legacy
scenes:
  1A: compiled
"""


def _add_manifest(root: Path) -> None:
    (root / "ownership.yaml").write_text(_OWNERSHIP, encoding="utf-8")


def test_two_owners_fixture_adds_only_the_manifest(tmp_path: Path) -> None:
    baseline = load_tree(copy_fixture("mini_ok", tmp_path / "baseline"))
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _add_manifest(root)

    actual = load_tree(root)
    expected = {**baseline, "ownership.yaml": {"schema": 1, "catalog": "legacy", "scenes": {"1A": "compiled"}}}
    assert actual == expected
    assert list(actual["ownership.yaml"]) == ["schema", "catalog", "scenes"]


def test_compiled_scene_with_legacy_definition_reports_ownership(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean) == []
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _add_manifest(root)

    diagnostics = story_source.check_source_tree(root)
    diagnostic = next(item for item in diagnostics if item.name == "L2.ownership")
    assert diagnostic.file == "ownership.yaml"
    assert diagnostic.field == "scenes"
    assert "ownership.yaml" in diagnostic.message
    assert "scenes/1A.yaml" in diagnostic.message
    with pytest.raises(story_source.SourceError):
        story_source.compile_source_tree(root)
