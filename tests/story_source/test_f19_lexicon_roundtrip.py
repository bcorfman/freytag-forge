from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import copy_fixture, load_tree, require_story_source

_MEMORY_NAMES = ["memory card", "card", "Michelle's card", "the card"]
_MEMORY_HIDDEN_NAMES = ["hidden card", "hidden memory card"]
_BASE_LEAK_TERMS = [
    "memory card",
    "hidden memory card",
    "hidden card",
    "Michelle's card",
    "the card",
    "taped beneath the drawer",
    "taped under the drawer",
    "taped to the drawer",
    "memory card recovered",
]


def _replace_shared_value(root: Path, field: str, value: object) -> None:
    path = root / "scenes/1A.match.yaml"
    document = load_tree(root)["scenes/1A.match.yaml"]
    document["shared"]["drawer_search"][field] = value
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _set_match_options(root: Path, scene: str, *, lexicon: bool, plural_twins: bool) -> None:
    path = root / f"scenes/{scene}.match.yaml"
    document = load_tree(root)[f"scenes/{scene}.match.yaml"]
    ordered = {
        "schema": document["schema"],
        "scene": document["scene"],
        "lexicon": lexicon,
        "plural_twins": plural_twins,
    }
    ordered.update({key: document[key] for key in ("shared", "claims", "deliveries") if key in document})
    path.write_text(yaml.safe_dump(ordered, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _write_lexicon(root: Path) -> None:
    document = {
        "schema": 1,
        "entities": {
            "memory_card": {"names": _MEMORY_NAMES, "hidden_names": _MEMORY_HIDDEN_NAMES},
            "michelle_drawer": {"names": ["drawer", "KMS", "workstation", "drawer's"]},
        },
        "concepts": {"dead_drop": {"names": ["dead drop", "exchange point"]}},
        "verb_classes": {"connect": {"words": ["plug", "insert", "connect"]}},
    }
    (root / "lexicon.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )


def _write_lock(root: Path) -> None:
    document = {
        "schema": 1,
        "scene": "1A",
        "generated_by": "story lock",
        "claims": {
            "k_sl_1a_b_r0": {
                "must_convey": [
                    ["memory card", "card", "Michelle's card", "the card", "hidden card", "hidden memory card"],
                    ["taped"],
                    ["beneath the KMS drawer", "under the KMS drawer", "beneath the drawer"],
                    ["Michelle", "Michelle's", "Dr. McGehee", "Michelle McGehee", "Shelly"],
                ],
                "leak_terms": _BASE_LEAK_TERMS,
            },
            "k_sl_1a_b_r0w": {
                "must_convey": [
                    ["memory card", "card", "Michelle's card", "the card", "hidden card", "hidden memory card"],
                    ["taped"],
                    ["beneath the KMS drawer", "under the KMS drawer", "beneath the drawer"],
                    ["Michelle", "Michelle's", "Dr. McGehee", "Michelle McGehee", "Shelly"],
                ],
                "leak_terms": _BASE_LEAK_TERMS,
            },
        },
        "deliveries": {},
    }
    path = root / "scenes/1A.match.lock.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _build_roundtrip_fixture(root: Path) -> None:
    _set_match_options(root, "1A", lexicon=True, plural_twins=True)
    _replace_shared_value(root, "must_convey", [{"from": ["$memory_card.all"]}])
    _replace_shared_value(
        root,
        "leak_terms",
        {
            "from": ["$memory_card.all"],
            "add": [
                "taped beneath the drawer",
                "taped under the drawer",
                "taped to the drawer",
                "memory card recovered",
                "saved file(s)",
            ],
            "drop": ["saved file", "saved files"],
        },
    )
    _write_lexicon(root)
    _write_lock(root)


def _assert_only_changed(before: dict[str, object], after: dict[str, object], changed: set[str]) -> None:
    assert set(after) - set(before) == {"lexicon.yaml", "scenes/1A.match.lock.yaml"}
    assert {path for path in after if after.get(path) != before.get(path)} == changed | {
        "lexicon.yaml",
        "scenes/1A.match.lock.yaml",
    }
    for path in set(before) - changed:
        assert after[path] == before[path]


def _canonical_json(package: object) -> str:
    return json.dumps(asdict(package), sort_keys=True, default=str)


def test_lexicon_roundtrip_tree_has_only_lexicon_inputs_and_lock(tmp_path: Path) -> None:
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")
    baseline = load_tree(baseline_root)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _build_roundtrip_fixture(root)

    mutated = load_tree(root)
    _assert_only_changed(baseline, mutated, {"scenes/1A.match.yaml"})
    assert mutated["scenes/1A.match.yaml"]["lexicon"] is True
    assert mutated["scenes/1A.match.yaml"]["plural_twins"] is True
    assert mutated["scenes/1A.match.yaml"]["shared"]["drawer_search"]["must_convey"][0] == {
        "from": ["$memory_card.all"]
    }
    assert mutated["scenes/1A.match.lock.yaml"]["scene"] == "1A"


def test_equivalent_lexicon_lock_compiles_to_the_f01_package(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _build_roundtrip_fixture(root)
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")

    assert story_source.check_source_tree(baseline_root) == []
    assert story_source.check_source_tree(root) == []
    assert story_source.compile_source_tree(root) == story_source.compile_source_tree(baseline_root)


def test_story_expand_roundtrip_without_lexicon_keeps_canonical_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story_source = require_story_source()
    story_cli = pytest.importorskip("storygame.story_cli")
    root = copy_fixture("mini_ok", tmp_path / "expanded")
    _build_roundtrip_fixture(root)
    baseline_root = copy_fixture("mini_ok", tmp_path / "baseline")

    assert story_source.check_source_tree(baseline_root) == []
    assert story_source.check_source_tree(root) == []
    expected = story_source.compile_source_tree(baseline_root)
    monkeypatch.chdir(root)
    assert story_cli.main(["expand", "1A"]) == 0
    expanded = load_tree(root)
    assert expanded["scenes/1A.match.yaml"]["lexicon"] is False
    (root / "lexicon.yaml").unlink()
    assert _canonical_json(story_source.compile_source_tree(root)) == _canonical_json(expected)
