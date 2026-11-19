from __future__ import annotations

import json
from pathlib import Path

from storygame.story_source.compiler import compile_source_tree
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

PACKAGE = Path(__file__).resolve().parents[2] / "data" / "stories" / "continuity-initiative"


def test_compiled_story_copy_contains_only_source_and_ownership(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)

    assert (root / "source").is_dir()
    assert (root / "ownership.yaml").is_file()
    assert not {
        "plot.md",
        "storylets.md",
        "world.yaml",
        "knowledge.yaml",
        "storylet-routes.yaml",
        "handoffs.yaml",
        "incidents.yaml",
        "pacing.yaml",
        "connections.yaml",
    } & {path.name for path in root.iterdir()}


def test_compiled_story_copy_matches_compiled_source_tree(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)

    assert load_compiled_copy(root).model_dump() == compile_source_tree(PACKAGE / "source").model_dump()


def test_patching_compiled_story_copy_reaches_loaded_package(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(root / "source", "scenes/1A.yaml", "entry", "PATCHED")

    assert "PATCHED" in json.dumps(load_compiled_copy(root).model_dump(), default=str)


def test_compiled_story_copy_cache_isolated_by_directory(tmp_path: Path) -> None:
    first = compiled_story_copy(tmp_path / "first")
    second = compiled_story_copy(tmp_path / "second")
    patch_source(first / "source", "scenes/1A.yaml", "entry", "FIRST PATCH")
    patch_source(second / "source", "scenes/1A.yaml", "entry", "SECOND PATCH")

    first_dump = json.dumps(load_compiled_copy(first).model_dump(), default=str)
    second_dump = json.dumps(load_compiled_copy(second).model_dump(), default=str)
    assert "FIRST PATCH" in first_dump
    assert "FIRST PATCH" not in second_dump
    assert "SECOND PATCH" in second_dump
    assert "SECOND PATCH" not in first_dump
