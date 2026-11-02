from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.phase1 import act2_probe, check_act2_probe
from storygame.runtime.delivery_text import resolve_delivery_text
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
INCIDENTS = {incident.scene_id: incident for incident in PACKAGE.incidents if incident.scene_id in act2_probe.SCENES}


@pytest.mark.parametrize(
    ("scene", "successor"),
    [("2A", "2B"), ("2B", "2C"), ("2C", "3A")],
)
def test_dry_run_none_reaches_successor_and_passes_checker(tmp_path: Path, scene: str, successor: str) -> None:
    assert act2_probe.run(tmp_path, scene, 1, True, False, "none") == 0
    assert check_act2_probe.check(tmp_path, 1, "dry") == []
    row = json.loads((tmp_path / "results.json").read_text())["rows"][0]
    assert row["scene"] == scene
    assert row["final_scene"] == successor
    assert row["successor_entry_variants_seen"]
    assert row["turns"]
    assert len(row["turns"]) == len(row["commands"])
    assert row["final_true_facts"] == sorted(row["final_true_facts"])
    assert row["repeated_response_streak_max"] >= 1
    assert row["stuck_loop"] is (row["repeated_response_streak_max"] >= 3)


@pytest.mark.parametrize("scene", act2_probe.SCENES)
@pytest.mark.parametrize("prefix", ["missed_window", "stall"])
def test_dry_run_prefixes_use_only_the_prefix_budget_and_pass_checker(tmp_path: Path, scene: str, prefix: str) -> None:
    assert act2_probe.run(tmp_path, scene, 1, True, False, prefix) == 0
    assert check_act2_probe.check(tmp_path, 1, "dry") == []
    row = json.loads((tmp_path / "results.json").read_text())["rows"][0]
    assert row["prefix"] == prefix
    assert row["scripted_turns"] == min(len(act2_probe.SCRIPTED_PREFIXES[prefix][scene]), row["turns_in_scene"])
    assert [turn["scripted"] for turn in row["turns"][: row["scripted_turns"]]] == [True] * row["scripted_turns"]
    assert not any(turn["scripted"] for turn in row["turns"][row["scripted_turns"] :])
    assert row["nudge_seen_turn"] == 6
    assert row["exit_seen_turn"] is not None
    if scene == "2C":
        assert row["unearned_facts"] == []
        assert not {
            "committed_to_transmit",
            "committed_to_rescue",
            "detention_sectors_sealed",
            "evidence_not_transmitted",
        } & set(row["final_true_facts"])


@pytest.mark.parametrize("scene", act2_probe.SCENES)
def test_exit_cause_classifier_declared_outcomes_and_neutral_recovery(scene: str) -> None:
    incident = INCIDENTS[scene]
    for outcome in incident.outcomes:
        facts = set(outcome.advantages)
        assert act2_probe.classify_exit_cause(facts, incident) == outcome.id
    assert act2_probe.classify_exit_cause(
        {"purge_recovery_ready"}, incident if scene == "2C" else INCIDENTS["2C"], True
    ) == ("neutral_recovery")


def test_live_mode_without_confirm_refuses(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="requires --confirm"):
        act2_probe.run(tmp_path, "2A", 1, False, False, "none")


def test_checker_rejects_doctored_2c_recovery_outcome_fact(tmp_path: Path) -> None:
    assert act2_probe.run(tmp_path, "2C", 1, True, False, "missed_window") == 0
    path = tmp_path / "results.json"
    artifact = json.loads(path.read_text())
    artifact["rows"][0]["final_true_facts"].append("committed_to_transmit")
    artifact["rows"][0]["final_true_facts"].sort()
    path.write_text(json.dumps(artifact), encoding="utf-8")
    errors = check_act2_probe.check(tmp_path, 1, "dry")
    assert any("2C recovery cannot assert outcome facts" in error for error in errors)


def test_dry_run_erased_ledger_reaches_successor_and_passes_checker(tmp_path: Path) -> None:
    assert act2_probe.run(tmp_path, "2C", 1, True, False, "none", "erased") == 0
    assert check_act2_probe.check(tmp_path, 1, "dry") == []
    row = json.loads((tmp_path / "results.json").read_text())["rows"][0]
    assert row["ledger"] == "erased"
    assert row["final_scene"] == "3A"


def test_state_supports_both_2c_ledgers() -> None:
    kept = act2_probe._state(PACKAGE, "2C")
    erased = act2_probe._state(PACKAGE, "2C", "erased")
    kept_facts = {fact.predicate for fact in kept.facts.asserted}
    erased_facts = {fact.predicate for fact in erased.facts.asserted}
    assert "brandon_name_kept" in kept_facts
    assert "brandon_name_erased" not in kept_facts
    assert {"brandon_name_erased", "evidence_gap_development_record"} <= erased_facts
    assert "brandon_name_kept" not in erased_facts


def test_erased_ledger_is_only_valid_for_2c(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ledger erased applies only to scene 2C"):
        act2_probe.run(tmp_path, "2A", 1, True, False, "none", "erased")
    with pytest.raises(ValueError, match="unknown ledger"):
        act2_probe.run(tmp_path, "2C", 1, True, False, "none", "other")


def test_checker_validates_2c_ledger_delivery_sentence(tmp_path: Path) -> None:
    assert act2_probe.run(tmp_path, "2C", 1, True, False, "none") == 0
    path = tmp_path / "results.json"
    artifact = json.loads(path.read_text())
    row = artifact["rows"][0]
    reveal_turn = next(index for index, turn in enumerate(row["turns"]) if "k_sl_2c_c_r1" in turn["committed_reveals"])
    row["responses"][reveal_turn] = "He glances at Kristin as he says it."
    path.write_text(json.dumps(artifact), encoding="utf-8")
    assert check_act2_probe.check(tmp_path, 1, "dry")
    row["responses"][reveal_turn] = "He says it coldly and avoids Kristin's eyes."
    path.write_text(json.dumps(artifact), encoding="utf-8")
    assert check_act2_probe.check(tmp_path, 1, "dry") == []


@pytest.mark.parametrize(
    ("ledger", "sentence"),
    [
        ("kept", "He says it coldly and avoids Kristin's eyes."),
        ("erased", "He glances at Kristin as he says it."),
    ],
)
def test_real_package_selects_2c_delivery_variant(ledger: str, sentence: str) -> None:
    item = next(item for item in PACKAGE.knowledge.knowledge if item.id == "k_sl_2c_c_r1")
    state = act2_probe._state(PACKAGE, "2C", ledger)
    assert sentence in (resolve_delivery_text(item, {fact.predicate for fact in state.facts.asserted}) or "")
