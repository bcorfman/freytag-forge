from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import storygame.story_package.loader as loader
from storygame.story_package import StoryPackageError, load_story_package

PACKAGE = Path("data/stories/continuity-initiative")


def copied_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE, destination)
    return destination


def test_repeated_load_returns_the_cached_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = copied_package(tmp_path)
    uncached = loader._load_story_package_uncached
    calls = 0

    def spy(package_root: Path):
        nonlocal calls
        calls += 1
        return uncached(package_root)

    monkeypatch.setattr(loader, "_load_story_package_uncached", spy)

    first = load_story_package(root)
    second = load_story_package(root)

    assert first is second
    assert calls == 1


def test_edited_package_is_reloaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = copied_package(tmp_path)
    uncached = loader._load_story_package_uncached
    calls = 0

    def spy(package_root: Path):
        nonlocal calls
        calls += 1
        return uncached(package_root)

    monkeypatch.setattr(loader, "_load_story_package_uncached", spy)

    original = load_story_package(root)
    plot = root / "plot.md"
    plot.write_text(
        plot.read_text(encoding="utf-8").replace("**Genre:** Adventure / Conspiracy Thriller", "**Genre:** Mystery"),
        encoding="utf-8",
    )
    edited = load_story_package(root)

    assert edited is not original
    assert edited.genre == "Mystery"
    assert calls == 2


def test_failed_load_is_not_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = copied_package(tmp_path)
    (root / "world.yaml").write_text("not: [valid", encoding="utf-8")
    uncached = loader._load_story_package_uncached
    calls = 0

    def spy(package_root: Path):
        nonlocal calls
        calls += 1
        return uncached(package_root)

    monkeypatch.setattr(loader, "_load_story_package_uncached", spy)

    with pytest.raises(StoryPackageError):
        load_story_package(root)
    with pytest.raises(StoryPackageError):
        load_story_package(root)

    assert calls == 2
