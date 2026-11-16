from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree, patch_source


def test_observes_fixture_changes_only_observed_by(tmp_path: Path) -> None:
    baseline = load_tree(copy_fixture("mini_ok", tmp_path / "baseline"))
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(
        root,
        "scenes/2C.yaml",
        "incidents[i_2c_rebecca_corridor].observed_by",
        ["k_sl_2c_c_r1", "k_sl_2c_d_r4"],
    )

    expected = copy.deepcopy(baseline)
    expected["scenes/2C.yaml"]["incidents"][0]["observed_by"] = [  # type: ignore[index]
        "k_sl_2c_c_r1",
        "k_sl_2c_d_r4",
    ]
    assert load_tree(root) == expected


def test_missing_outcome_observation_is_reported(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean) == []

    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(
        root,
        "scenes/2C.yaml",
        "incidents[i_2c_rebecca_corridor].observed_by",
        ["k_sl_2c_c_r1", "k_sl_2c_d_r4"],
    )
    with pytest.raises(story_source.SourceError) as error:
        story_source.compile_source_tree(root)

    diagnostic = next(item for item in error.value.diagnostics if item.name == "L2.incident_observes_outcomes")
    assert diagnostic.file == "scenes/2C.yaml"
    assert diagnostic.field == "observed_by"
