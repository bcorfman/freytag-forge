from __future__ import annotations

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

PACKAGE_ROOT = Path("data/stories/continuity-initiative")


def _knowledge() -> dict[str, dict]:
    raw = yaml.safe_load((PACKAGE_ROOT / "knowledge.yaml").read_text())
    return {item["id"]: item for item in raw["knowledge"]}


def _matches(knowledge: dict[str, dict], command: str) -> set[str]:
    return {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith("k_sl_2c")
        and item.get("action_evidence")
        and _matches_all(tuple(tuple(group) for group in item["action_evidence"]), command)
    }


def test_2c_assess_and_evaluate_verbs_match_unique_reveals() -> None:
    knowledge = _knowledge()
    cases = {
        "Assess the executive channel's private offer and whether the people running this are turning on each other.": {
            "k_sl_2c_a_r1"
        },
        # Full engine coverage for the established reveal is in test_2c_assess_engine_turn.py.
        "Assess the cost of transmitting our evidence right now to the people still held here.": {"k_sl_2c_c_r2"},
        "Weigh the private offer.": {"k_sl_2c_a_r1"},
        "Evaluate the cost of sending our evidence now.": {"k_sl_2c_c_r2"},
        "Read the private message and discuss the offer.": {"k_sl_2c_a_r1"},
        "Assess the weather.": set(),
        "Weigh my laptop.": set(),
        "Evaluate the kitchen.": set(),
    }
    for command, expected in cases.items():
        assert _matches(knowledge, command) == expected, command


def test_2c_action_contract_positives_remain_unique() -> None:
    knowledge = _knowledge()
    for item_id in ("k_sl_2c_a_r1", "k_sl_2c_c_r2"):
        for command in knowledge[item_id].get("action_contract", {}).get("positive", []):
            assert _matches(knowledge, command) == {item_id}, (item_id, command)


def test_2c_edited_items_keep_two_evidence_groups() -> None:
    knowledge = _knowledge()
    assert len(knowledge["k_sl_2c_a_r1"]["action_evidence"]) == 2
    assert len(knowledge["k_sl_2c_c_r2"]["action_evidence"]) == 2
