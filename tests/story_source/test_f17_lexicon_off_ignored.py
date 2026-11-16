from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import copy_fixture, load_tree


def _set_match_options(root: Path, scene: str, *, lexicon: bool) -> None:
    path = root / f"scenes/{scene}.match.yaml"
    document = load_tree(root)[f"scenes/{scene}.match.yaml"]
    ordered = {"schema": document["schema"], "scene": document["scene"], "lexicon": lexicon}
    ordered.update({key: document[key] for key in ("shared", "claims", "deliveries") if key in document})
    path.write_text(yaml.safe_dump(ordered, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _assert_only_changed(before: dict[str, object], after: dict[str, object], changed: set[str]) -> None:
    assert set(after) - set(before) == {"lexicon.yaml"}
    assert {path for path in after if after.get(path) != before.get(path)} == changed | {"lexicon.yaml"}
    for path in set(before) - changed:
        assert after[path] == before[path]


def test_malformed_lexicon_is_added_but_both_scenes_are_explicitly_off(tmp_path: Path) -> None:
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")
    baseline = load_tree(baseline_root)
    root = copy_fixture("mini_ok", tmp_path / "mutated")

    _set_match_options(root, "1A", lexicon=False)
    _set_match_options(root, "2C", lexicon=False)
    (root / "lexicon.yaml").write_text(
        "schema: 1\nentities: broken\nconcepts: [not, a, mapping]\nverb_classes: nope\n",
        encoding="utf-8",
    )

    mutated = load_tree(root)
    _assert_only_changed(baseline, mutated, {"scenes/1A.match.yaml", "scenes/2C.match.yaml"})
    assert mutated["scenes/1A.match.yaml"]["lexicon"] is False
    assert mutated["scenes/2C.match.yaml"]["lexicon"] is False


def test_malformed_lexicon_is_ignored_when_every_scene_is_off(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _set_match_options(root, "1A", lexicon=False)
    _set_match_options(root, "2C", lexicon=False)
    (root / "lexicon.yaml").write_text(
        "schema: 1\nentities: broken\nconcepts: [not, a, mapping]\nverb_classes: nope\n",
        encoding="utf-8",
    )
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")

    assert story_source.check_source_tree(baseline_root) == []
    assert story_source.check_source_tree(root) == []
    story_source.compile_source_tree(root)
