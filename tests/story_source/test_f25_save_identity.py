from __future__ import annotations

import warnings
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree, patch_source

FROZEN_CLAIM_ID = "k_sl_1a_b_r0w"


@dataclass(frozen=True)
class _PackageIds:
    ids: dict[str, frozenset[str]]


def test_fixture_adds_only_the_retired_id_entry(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    baseline = load_tree(root)
    expected = deepcopy(baseline)
    retired_ids = {"claim": {FROZEN_CLAIM_ID: "claim removed from the package"}}

    patch_source(root, "story.yaml", "retired_ids", retired_ids)
    expected["story.yaml"]["retired_ids"] = retired_ids

    mutated = load_tree(root)
    assert mutated == expected
    assert mutated != baseline


def test_missing_frozen_id_warns_then_retired_id_is_silent(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    clean_root = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean_root) == []

    package = _PackageIds({"claim": frozenset({"k_sl_1a_b_r0", "k_scene_1a_entry"})})
    manifest = {"claim": [FROZEN_CLAIM_ID]}

    with pytest.warns(UserWarning, match=FROZEN_CLAIM_ID):
        story_source.check_save_identity(package, manifest, retired_ids={})

    retired_ids = {"claim": {FROZEN_CLAIM_ID: "claim removed from the package"}}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        story_source.check_save_identity(package, manifest, retired_ids=retired_ids)
    assert caught == []
