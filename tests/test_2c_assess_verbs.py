from __future__ import annotations

from pathlib import Path

from storygame.runtime.candidate_matcher import _matches_all
from storygame.story_package.loader import load_story_package

PACKAGE_ROOT = Path("data/stories/continuity-initiative")


def _knowledge() -> dict[str, dict]:
    package = load_story_package(PACKAGE_ROOT)
    return {item.id: item.model_dump() for item in package.knowledge.knowledge}


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
        "Tell Rebecca my answer to her offer.": {"k_sl_2c_c_r1"},
        "Head to the broadcast uplink and transmit the copied JANUS files.": {"k_sl_2c_d_r3"},
        "Reach the transfer carts and rescue the prisoners.": {"k_sl_2c_d_r4"},
        "Read the private message and discuss the offer.": set(),
        "Assess the weather.": set(),
        "Weigh my laptop.": set(),
        "Evaluate the kitchen.": set(),
    }
    for command, expected in cases.items():
        assert _matches(knowledge, command) == expected, command


def test_2c_action_contract_positives_remain_unique() -> None:
    knowledge = _knowledge()
    for item_id in ("k_sl_2c_d_r3", "k_sl_2c_d_r4"):
        for command in (knowledge[item_id].get("action_contract") or {}).get("positive", []):
            assert _matches(knowledge, command) == {item_id}, (item_id, command)


def test_2c_edited_items_keep_two_evidence_groups() -> None:
    knowledge = _knowledge()
    assert len(knowledge["k_sl_2c_d_r3"]["action_evidence"]) == 2
    assert len(knowledge["k_sl_2c_d_r4"]["action_evidence"]) == 2
    assert len(knowledge["k_sl_2c_c_r1"]["action_evidence"]) == 2
