from __future__ import annotations

from pathlib import Path

import pytest

import storygame.story_package.loader as loader
from storygame.story_package import load_story_package
from storygame.story_package.loader import _validate_narration_term_traps
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

PACKAGE = Path("data/stories/continuity-initiative")


def test_continuity_package_has_no_authored_narration_term_traps() -> None:
    package = load_story_package(PACKAGE)

    assert package.story_id == "continuity_initiative"
    _validate_narration_term_traps(package)


def test_loader_rejects_an_uncommitted_guarded_term_in_scene_frame_situation(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(
        root,
        "source/scenes/1C.yaml",
        "situation",
        "A supposedly abandoned freight terminal above a dead drop.",
    )

    with pytest.raises(
        SourceError,
        match="scene 1C.*dead drop.*k_sl_1a_b_r1",
    ):
        load_compiled_copy(root)


def test_loader_runs_narration_term_trap_lint_without_authored_handoff_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = compiled_story_copy(tmp_path)
    package = load_story_package(PACKAGE)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "1A")
    entry = scene.metadata.entry_text.replace(
        "Michelle's text came in",
        "A genuine cooling-water pressure fault appeared. Michelle's text came in",
        1,
    )
    patch_source(root, "source/scenes/1A.yaml", "entry", entry)
    monkeypatch.setattr(loader, "_validate_authored_handoffs", lambda package: None)

    with pytest.raises(
        SourceError,
        match="scene 1A.*cooling-water pressure fault.*k_sl_2a_c_r5",
    ):
        load_compiled_copy(root)
