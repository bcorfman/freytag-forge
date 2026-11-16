from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import copy_fixture, load_tree, patch_source


def _add_cycle_exit(root: Path) -> dict[str, object]:
    scene_path = root / "scenes/2C.yaml"
    scene = load_tree(root)["scenes/2C.yaml"]
    assert isinstance(scene, dict)
    exit_record = {
        "id": "t_2c_1a",
        "to": "1A",
        "priority": 1,
        "when_all": ["evacuation_complete"],
        "bridge": "The recovery route loops back to Michelle's house.",
    }
    scene["exit"] = exit_record
    keys = list(scene)
    keys.insert(keys.index("ending"), keys.pop(keys.index("exit")))
    ordered_scene = {key: scene[key] for key in keys}
    scene_path.write_text(
        yaml.safe_dump(ordered_scene, sort_keys=False, width=10_000, allow_unicode=True),
        encoding="utf-8",
    )
    return exit_record


def test_cycles_fixture_changes_only_the_cycle_inputs(tmp_path: Path) -> None:
    baseline = load_tree(copy_fixture("mini_ok", tmp_path / "baseline"))
    root = copy_fixture("mini_ok", tmp_path / "mutated")

    patch_source(
        root,
        "scenes/1A.yaml",
        "reveals[find_card].variants.quiet.when",
        {"memory_card_recovered": True},
    )
    exit_record = _add_cycle_exit(root)

    expected = copy.deepcopy(baseline)
    expected["scenes/1A.yaml"]["reveals"][0]["variants"]["quiet"]["when"] = {  # type: ignore[index]
        "memory_card_recovered": True
    }
    expected_scene = expected["scenes/2C.yaml"]
    expected_scene["exit"] = exit_record  # type: ignore[index]
    expected_keys = list(expected_scene)
    expected_keys.insert(expected_keys.index("ending"), expected_keys.pop(expected_keys.index("exit")))
    expected["scenes/2C.yaml"] = {key: expected_scene[key] for key in expected_keys}

    actual = load_tree(root)
    assert actual == expected
    assert list(actual["scenes/2C.yaml"]) == [*list(baseline["scenes/2C.yaml"])[:-1], "exit", "ending"]


def test_cycles_are_reported_as_source_error(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean) == []

    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(
        root,
        "scenes/1A.yaml",
        "reveals[find_card].variants.quiet.when",
        {"memory_card_recovered": True},
    )
    _add_cycle_exit(root)

    with pytest.raises(story_source.SourceError) as error:
        story_source.compile_source_tree(root)
    assert "L2.cycles" in {diagnostic.name for diagnostic in error.value.diagnostics}
