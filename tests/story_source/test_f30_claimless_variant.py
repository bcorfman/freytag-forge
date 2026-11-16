from __future__ import annotations

from pathlib import Path

import pytest

from tests.story_source.helpers import DELETE, copy_fixture, load_tree, patch_source


def test_claimless_variant_removes_only_claimed_passage_fields_and_match_entry(tmp_path: Path) -> None:
    baseline = copy_fixture("mini_ok", tmp_path / "baseline")
    root = copy_fixture("mini_ok", tmp_path / "changed")
    for address in ("claim_id", "says", "text"):
        patch_source(root, "scenes/1A.yaml", f"reveals[find_card].variants.quiet.{address}", DELETE)
    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0", DELETE)

    baseline_tree = load_tree(baseline)
    changed_tree = load_tree(root)
    assert set(changed_tree) == set(baseline_tree)
    expected_changed = {
        "scenes/1A.yaml",
        "scenes/1A.match.yaml",
    }
    assert {path for path in baseline_tree if baseline_tree[path] != changed_tree[path]} == expected_changed
    quiet = changed_tree["scenes/1A.yaml"]["reveals"][0]["variants"]["quiet"]
    assert set(quiet) == {"realization_id", "intent", "from_outline", "commits", "when", "voiceable"}
    assert "k_sl_1a_b_r0" not in changed_tree["scenes/1A.match.yaml"]["claims"]
    assert all(changed_tree[path] == baseline_tree[path] for path in baseline_tree if path not in expected_changed)


def test_claimless_variant_compiles_without_a_knowledge_claim(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    root = copy_fixture("mini_ok", tmp_path)
    for address in ("claim_id", "says", "text"):
        patch_source(root, "scenes/1A.yaml", f"reveals[find_card].variants.quiet.{address}", DELETE)
    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0", DELETE)
    clean_root = copy_fixture("mini_ok", tmp_path / "clean")

    assert story_source.check_source_tree(root) == []
    assert story_source.check_source_tree(clean_root) == []
    package = story_source.compile_source_tree(root)
    claims = [claim for claim in package.knowledge.knowledge if claim.source.realization_id == "SL-1A-E-R1"]
    assert claims == []
