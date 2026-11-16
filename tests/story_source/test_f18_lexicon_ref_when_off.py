from __future__ import annotations

from pathlib import Path

import yaml

from tests.story_source.helpers import copy_fixture, load_tree, require_story_source


def _replace_mapping_value(root: Path, field: str, value: object) -> None:
    path = root / "scenes/1A.match.yaml"
    document = load_tree(root)["scenes/1A.match.yaml"]
    document["shared"]["drawer_search"][field] = value
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _assert_only_changed(before: dict[str, object], after: dict[str, object], changed: set[str]) -> None:
    assert set(after) == set(before)
    assert {path for path in after if after[path] != before[path]} == changed
    for path in set(before) - changed:
        assert after[path] == before[path]


def test_lexicon_reference_without_flag_changes_only_one_match_group(tmp_path: Path) -> None:
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")
    baseline = load_tree(baseline_root)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _replace_mapping_value(root, "must_convey", [{"from": ["$memory_card"]}])

    mutated = load_tree(root)
    _assert_only_changed(baseline, mutated, {"scenes/1A.match.yaml"})
    assert mutated["scenes/1A.match.yaml"]["shared"]["drawer_search"]["must_convey"][0] == {"from": ["$memory_card"]}


def test_lexicon_reference_is_rejected_when_scene_is_off(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _replace_mapping_value(root, "must_convey", [{"from": ["$memory_card"]}])
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")

    assert story_source.check_source_tree(baseline_root) == []
    diagnostics = story_source.check_source_tree(root)
    assert [diagnostic.name for diagnostic in diagnostics] == ["L1.lexicon_off"]
    assert diagnostics[0].file == "scenes/1A.match.yaml"
