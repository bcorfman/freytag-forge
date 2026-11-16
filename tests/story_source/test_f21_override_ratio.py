from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import copy_fixture, load_tree

_FIVE_NAMES = ["memory card", "card", "Michelle's card", "the card", "recovered card"]
_SEVEN_ALIASES = _FIVE_NAMES + ["extra alias one", "extra alias two"]


def _replace_claim_aliases(root: Path, value: object) -> None:
    path = root / "scenes/1A.match.yaml"
    document = load_tree(root)["scenes/1A.match.yaml"]
    document["claims"]["k_sl_1a_b_r0"]["aliases"] = value
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _set_match_options(root: Path) -> None:
    path = root / "scenes/1A.match.yaml"
    document = load_tree(root)["scenes/1A.match.yaml"]
    ordered = {"schema": document["schema"], "scene": document["scene"], "lexicon": True}
    ordered.update({key: document[key] for key in ("shared", "claims", "deliveries") if key in document})
    path.write_text(yaml.safe_dump(ordered, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _write_lexicon(root: Path) -> None:
    document = {
        "schema": 1,
        "entities": {"memory_card": {"names": _FIVE_NAMES, "hidden_names": []}},
        "concepts": {},
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
        "claims": {"k_sl_1a_b_r0": {"aliases": _SEVEN_ALIASES}},
        "deliveries": {},
    }
    (root / "scenes/1A.match.lock.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )


def _build_ratio_fixture(root: Path) -> None:
    _set_match_options(root)
    _replace_claim_aliases(root, {"from": ["$memory_card"], "add": ["extra alias one", "extra alias two"]})
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


def test_override_ratio_fixture_has_two_adds_to_five_expanded_names(tmp_path: Path) -> None:
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")
    baseline = load_tree(baseline_root)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _build_ratio_fixture(root)

    mutated = load_tree(root)
    _assert_only_changed(baseline, mutated)
    assert mutated["scenes/1A.match.yaml"]["claims"]["k_sl_1a_b_r0"]["aliases"] == {
        "from": ["$memory_card"],
        "add": ["extra alias one", "extra alias two"],
    }
    assert mutated["scenes/1A.match.lock.yaml"]["claims"]["k_sl_1a_b_r0"]["aliases"] == _SEVEN_ALIASES


def test_override_ratio_is_over_gate_but_build_still_passes(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _build_ratio_fixture(root)
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")

    assert story_source.check_source_tree(baseline_root) == []
    assert story_source.check_source_tree(root) == []
    rows = story_source.override_ratio(root)
    row = next(row for row in rows if row["scene"] == "1A" and row["field"] == "aliases")
    assert row["expanded"] == 5
    assert row["added"] == 2
    assert row["dropped"] == 0
    assert row["ratio"] == 0.4
    assert row["status"] == "over"
    assert story_source.pass2_gate(root) is False
    story_source.compile_source_tree(root)
