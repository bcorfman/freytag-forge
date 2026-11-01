from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import storygame.story_package.loader as loader
from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_package.loader import _validate_narration_term_traps

PACKAGE = Path("data/stories/continuity-initiative")


def test_continuity_package_has_no_authored_narration_term_traps() -> None:
    package = load_story_package(PACKAGE)

    assert package.story_id == "continuity_initiative"
    _validate_narration_term_traps(package)


def test_loader_rejects_an_uncommitted_guarded_term_in_scene_frame_situation(tmp_path: Path) -> None:
    root = tmp_path / "package"
    shutil.copytree(PACKAGE, root)
    knowledge = root / "knowledge.yaml"
    contents = knowledge.read_text(encoding="utf-8")
    contents = contents.replace(
        "situation: >-\n"
        "    The freight terminal has loading docks above a service level.\n"
        "    The observation shaft overlooks the processing line.\n"
        "    The service entrance is at the freight terminal.",
        "situation: A supposedly abandoned freight terminal above a dead drop.",
        1,
    )
    knowledge.write_text(contents, encoding="utf-8")

    with pytest.raises(
        StoryPackageError,
        match="scene 1C.*dead drop.*k_sl_1a_b_r1",
    ):
        load_story_package(root)


def test_loader_runs_narration_term_trap_lint_without_authored_handoff_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "package"
    shutil.copytree(PACKAGE, root)
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    contents = contents.replace(
        "entry_text: \"Michelle's text came in",
        "entry_text: \"A genuine cooling-water pressure fault appeared. Michelle's text came in",
        1,
    )
    plot.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(loader, "_validate_authored_handoffs", lambda package: None)

    with pytest.raises(
        StoryPackageError,
        match="scene 1A.*cooling-water pressure fault.*k_sl_2a_c_r5",
    ):
        load_story_package(root)
