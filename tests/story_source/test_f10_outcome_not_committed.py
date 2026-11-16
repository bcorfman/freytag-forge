from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree, patch_source


def test_outcome_fixture_changes_only_the_advantage(tmp_path: Path) -> None:
    baseline = load_tree(copy_fixture("mini_ok", tmp_path / "baseline"))
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(
        root,
        "scenes/2C.yaml",
        "reveals[michelle_changes_the_choice].variants.transmit.outcome.advantages",
        ["evidence_not_transmitted"],
    )

    expected = copy.deepcopy(baseline)
    expected["scenes/2C.yaml"]["reveals"][1]["variants"]["transmit"]["outcome"]["advantages"] = [  # type: ignore[index]
        "evidence_not_transmitted"
    ]
    assert load_tree(root) == expected


def test_uncommitted_outcome_is_rejected_by_the_loader(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean) == []

    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(
        root,
        "scenes/2C.yaml",
        "reveals[michelle_changes_the_choice].variants.transmit.outcome.advantages",
        ["evidence_not_transmitted"],
    )
    with pytest.raises(story_source.SourceError):
        story_source.compile_source_tree(root)
