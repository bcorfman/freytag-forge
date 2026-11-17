from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package.loader import StoryPackageError, load_legacy_story_package, load_story_package
from storygame.story_source.compiler import compile_source_tree

PACKAGE = Path(__file__).resolve().parents[1] / "data" / "stories" / "continuity-initiative"
LEGACY = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "parity" / "continuity-initiative" / "legacy"


def copied_package(tmp_path: Path, name: str = "package") -> Path:
    """Copy the default story with its frozen legacy files and no ownership manifest."""
    destination = tmp_path / name
    shutil.copytree(PACKAGE, destination)
    (destination / "ownership.yaml").unlink()
    shutil.copytree(LEGACY, destination, dirs_exist_ok=True)
    return destination


def add_compiled_ownership(root: Path, *, catalog: str = "compiled", legacy_scene: str | None = None) -> None:
    story = yaml.safe_load((root / "source" / "story.yaml").read_text(encoding="utf-8"))
    scenes = {scene: "legacy" if scene == legacy_scene else "compiled" for scene in story["scenes"]}
    ownership = {"schema": 1, "catalog": catalog, "scenes": scenes}
    (root / "ownership.yaml").write_text(yaml.safe_dump(ownership, sort_keys=False), encoding="utf-8")


def delete_legacy_files(root: Path) -> None:
    for path in root.iterdir():
        if path.name in {"ownership.yaml", "source"}:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def test_absent_ownership_keeps_legacy_loading(tmp_path: Path) -> None:
    root = copied_package(tmp_path)

    assert load_story_package(root).model_dump() == load_legacy_story_package(root).model_dump()


def test_all_compiled_can_load_without_legacy_files(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    add_compiled_ownership(root)
    delete_legacy_files(root)

    assert load_story_package(root).model_dump() == compile_source_tree(root / "source").model_dump()


def test_all_compiled_ignores_corrupt_legacy_files(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    add_compiled_ownership(root)
    expected = compile_source_tree(root / "source")
    (root / "world.yaml").write_text("not: [valid", encoding="utf-8")

    assert load_story_package(root).model_dump() == expected.model_dump()


def test_mixed_ownership_is_rejected(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    add_compiled_ownership(root, legacy_scene="1A")

    with pytest.raises(StoryPackageError, match=r"mixed.*catalog.*scene:1A"):
        load_story_package(root)


def test_legacy_loader_ignores_compiled_ownership(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    expected = load_legacy_story_package(root)
    add_compiled_ownership(root)

    assert load_legacy_story_package(root).model_dump() == expected.model_dump()


def test_source_edits_invalidate_dispatch_cache(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    add_compiled_ownership(root)
    first = load_story_package(root)
    story_path = root / "source" / "story.yaml"
    story = yaml.safe_load(story_path.read_text(encoding="utf-8"))
    story["genre"] = "Changed genre"
    story_path.write_text(yaml.safe_dump(story, sort_keys=False), encoding="utf-8")

    second = load_story_package(root)

    assert second.model_dump() != first.model_dump()
    assert second.genre == "Changed genre"
