"""Core coverage for save identity warnings and override-ratio reporting."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import yaml

from tests.story_source.helpers import copy_fixture, load_tree, require_story_source


@dataclass(frozen=True)
class _PackageIds:
    ids: dict[str, frozenset[str]]


def test_save_identity_is_silent_when_every_frozen_id_is_present() -> None:
    story_source = require_story_source()
    package = _PackageIds({"claim": frozenset({"known_claim"})})
    manifest = {"schema": 1, "story": "story", "snapshot": "snapshot", "ids": {"claim": ["known_claim"]}}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        story_source.check_save_identity(package, manifest)

    assert caught == []


def test_override_ratio_without_a_lexicon_is_zero_and_ok(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    path = root / "scenes/1A.match.yaml"
    document = load_tree(root)["scenes/1A.match.yaml"]
    document["claims"]["k_sl_1a_b_r0"]["aliases"] = {"from": ["$not_defined"], "add": ["local name"]}
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000), encoding="utf-8")

    row = next(row for row in story_source.override_ratio(root) if row["field"] == "aliases")

    assert row["expanded"] == 0
    assert row["ratio"] == 0
    assert row["status"] == "ok"
    assert story_source.pass2_gate(root) is True
