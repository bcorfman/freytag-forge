from __future__ import annotations

from pathlib import Path

import check_three_c_probe as checker
import pytest
import three_c_probe as probe

from bench.core import load_variation
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]


def _arm_package(arm: str):
    variation = load_variation(probe.variation_paths((arm,))[arm])
    return variation, load_story_package(Path(variation["_package_path"]))


def test_families_diff_is_only_the_three_d_r2_phrases() -> None:
    _, pump = _arm_package("pump")
    _, families = _arm_package("families")
    d_r2 = "k_sl_3c_d_r2"
    changed = []
    for knowledge_id, item in pump.knowledge_indexes.by_id.items():
        if item.model_dump(mode="json") != families.knowledge_indexes.by_id[knowledge_id].model_dump(mode="json"):
            changed.append(knowledge_id)
    assert changed == [d_r2]
    pump_d2 = pump.knowledge_indexes.by_id[d_r2]
    family_d2 = families.knowledge_indexes.by_id[d_r2]
    assert len(family_d2.action_evidence) == len(pump_d2.action_evidence)
    assert family_d2.action_evidence[0][:-3] == pump_d2.action_evidence[0]
    assert family_d2.action_evidence[0][-3:] == (
        "broadcast a message to the families",
        "broadcast a response to the families",
        "broadcast an update to the families",
    )
    pump_entry = next(scene.metadata.entry_text for scene in pump.scenes if scene.metadata.scene_id == "3C")
    family_entry = next(scene.metadata.entry_text for scene in families.scenes if scene.metadata.scene_id == "3C")
    assert pump_entry == family_entry


def test_checker_accepts_live_carried_n12_artifacts() -> None:
    artifact = ROOT / "bench/results/stage7-3c-carried-n12"
    if not artifact.is_dir():
        pytest.skip("live carried n12 artifacts are not available")
    errors = checker.check(artifact, 12, "artifacts")
    if errors and all("differs from current package" in error for error in errors):
        pytest.skip("live carried n12 artifacts were recorded against an earlier package")
    assert errors == []


def test_checker_rejects_3c_chain_reveal_in_scripted_prefix() -> None:
    row = {"scripted_prefix": {"committed_reveal_ids": ["k_sl_3c_a_r1"]}}
    assert checker.scripted_prefix_has_chain_reveals(row)


def test_checker_allows_earned_3c_reveals_in_turns() -> None:
    row = {
        "committed_reveal_ids": ["k_sl_3c_a_r1", "k_sl_3c_b_r1"],
        "turns": [{"committed_reveals": ["k_sl_3c_a_r1", "k_sl_3c_b_r1"]}],
        "scripted_prefix": {"committed_reveal_ids": ["k_sl_3b_e_r1"]},
    }
    assert not checker.scripted_prefix_has_chain_reveals(row)
