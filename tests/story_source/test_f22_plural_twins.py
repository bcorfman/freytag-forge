from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import copy_fixture, load_tree


def _set_match_options(root: Path, *, plural_twins: bool) -> None:
    path = root / "scenes/1A.match.yaml"
    document = load_tree(root)["scenes/1A.match.yaml"]
    ordered = {
        "schema": document["schema"],
        "scene": document["scene"],
        "lexicon": True,
        "plural_twins": plural_twins,
    }
    ordered.update({key: document[key] for key in ("shared", "claims", "deliveries") if key in document})
    path.write_text(yaml.safe_dump(ordered, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _write_lexicon(root: Path) -> None:
    document = {
        "schema": 1,
        "entities": {},
        "concepts": {"saved_file": {"names": ["saved file(s)"]}},
        "verb_classes": {},
    }
    (root / "lexicon.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )


def _write_lock(root: Path) -> None:
    document = {
        "schema": 1,
        "scene": "1A",
        "generated_by": "story lock",
        "claims": {"k_sl_1a_b_r0": {"aliases": ["saved file", "saved files"]}},
        "deliveries": {},
    }
    (root / "scenes/1A.match.lock.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )


def _replace_claim_aliases(root: Path) -> None:
    path = root / "scenes/1A.match.yaml"
    document = load_tree(root)["scenes/1A.match.yaml"]
    document["claims"]["k_sl_1a_b_r0"]["aliases"] = {"from": ["$saved_file"]}
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _build_plural_fixture(root: Path, *, plural_twins: bool) -> None:
    _set_match_options(root, plural_twins=plural_twins)
    _replace_claim_aliases(root)
    _write_lexicon(root)
    _write_lock(root)


def _assert_only_changed(before: dict[str, object], after: dict[str, object]) -> None:
    changed = {"scenes/1A.match.yaml"}
    assert set(after) - set(before) == {"lexicon.yaml", "scenes/1A.match.lock.yaml"}
    assert {path for path in after if after.get(path) != before.get(path)} == changed | {
        "lexicon.yaml",
        "scenes/1A.match.lock.yaml",
    }
    for path in set(before) - changed:
        assert after[path] == before[path]


def test_plural_twin_on_and_off_trees_have_the_same_intended_change(tmp_path: Path) -> None:
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")
    baseline = load_tree(baseline_root)
    on_root = copy_fixture("mini_ok", tmp_path / "on")
    _build_plural_fixture(on_root, plural_twins=True)
    off_root = copy_fixture("mini_ok", tmp_path / "off")
    _build_plural_fixture(off_root, plural_twins=False)

    on_tree = load_tree(on_root)
    off_tree = load_tree(off_root)
    _assert_only_changed(baseline, on_tree)
    _assert_only_changed(baseline, off_tree)
    assert on_tree["scenes/1A.match.yaml"]["plural_twins"] is True
    assert off_tree["scenes/1A.match.yaml"]["plural_twins"] is False
    assert on_tree["scenes/1A.match.lock.yaml"]["claims"]["k_sl_1a_b_r0"]["aliases"] == [
        "saved file",
        "saved files",
    ]


def test_plural_twins_expand_to_two_entries_and_off_is_rejected(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    on_root = copy_fixture("mini_ok", tmp_path / "on")
    _build_plural_fixture(on_root, plural_twins=True)
    off_root = copy_fixture("mini_ok", tmp_path / "off")
    _build_plural_fixture(off_root, plural_twins=False)
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")

    assert story_source.check_source_tree(baseline_root) == []
    assert story_source.check_source_tree(on_root) == []
    off_diagnostics = story_source.check_source_tree(off_root)
    assert [diagnostic.name for diagnostic in off_diagnostics] == ["L1.plural_off"]
    assert off_diagnostics[0].file == "lexicon.yaml"
    with pytest.raises(story_source.SourceError):
        story_source.compile_source_tree(off_root)
    story_source.compile_source_tree(on_root)
