from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import copy_fixture, load_tree, require_story_source

_BASE_ALIASES = ["memory card recovered"]
_LOCK_ALIASES = ["memory card", "card", "Michelle's card", "the card", "hidden card", "hidden memory card"]


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
        "entities": {
            "memory_card": {
                "names": ["memory card", "card", "Michelle's card", "the card", "new card name"],
                "hidden_names": ["hidden card", "hidden memory card"],
            }
        },
        "concepts": {},
        "verb_classes": {},
    }
    (root / "lexicon.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )


def _write_stale_lock(root: Path) -> None:
    document = {
        "schema": 1,
        "scene": "1A",
        "generated_by": "story lock",
        "claims": {"k_sl_1a_b_r0": {"aliases": _LOCK_ALIASES}},
        "deliveries": {},
    }
    (root / "scenes/1A.match.lock.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )


def _build_stale_fixture(root: Path) -> None:
    _set_match_options(root)
    _replace_claim_aliases(root, {"from": ["$memory_card"]})
    _write_lexicon(root)
    _write_stale_lock(root)


def _assert_only_changed(before: dict[str, object], after: dict[str, object]) -> None:
    changed = {"scenes/1A.match.yaml"}
    assert set(after) - set(before) == {"lexicon.yaml", "scenes/1A.match.lock.yaml"}
    assert {path for path in after if after.get(path) != before.get(path)} == changed | {
        "lexicon.yaml",
        "scenes/1A.match.lock.yaml",
    }
    for path in set(before) - changed:
        assert after[path] == before[path]


def test_stale_lock_fixture_changes_only_lexicon_inputs_and_lock(tmp_path: Path) -> None:
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")
    baseline = load_tree(baseline_root)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _build_stale_fixture(root)

    mutated = load_tree(root)
    _assert_only_changed(baseline, mutated)
    assert mutated["scenes/1A.match.yaml"]["claims"]["k_sl_1a_b_r0"]["aliases"] == {"from": ["$memory_card"]}
    assert mutated["scenes/1A.match.lock.yaml"]["claims"]["k_sl_1a_b_r0"]["aliases"] == _LOCK_ALIASES


def test_stale_lock_names_claim_and_field(tmp_path: Path) -> None:
    story_source = require_story_source()
    pytest.skip("L2.lock_stale needs the pass 2 expander, which is not built yet (validator round 4)")
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _build_stale_fixture(root)
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")

    assert story_source.check_source_tree(baseline_root) == []
    diagnostics = story_source.check_source_tree(root)
    assert [diagnostic.name for diagnostic in diagnostics] == ["L2.lock_stale"]
    diagnostic = diagnostics[0]
    assert diagnostic.file == "scenes/1A.match.lock.yaml"
    assert diagnostic.field == "aliases"
    assert "k_sl_1a_b_r0" in diagnostic.message
    with pytest.raises(story_source.SourceError):
        story_source.compile_source_tree(root)
