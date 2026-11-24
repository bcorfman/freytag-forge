from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from factory.outcome_contract import classify_run

CASES = json.loads((Path(__file__).parent / "fixtures/outcome_contract/cases.json").read_text())
CORE_CASES = [case for case in CASES if case["tier"] == "core"]
EXTENSION_CASES = [case["id"] for case in CASES if case["tier"] != "core"]


def _assert_subset(actual: dict, expected: dict, case_id: str) -> None:
    for field, expected_value in expected.items():
        if field == "turns":
            for number, turn_expected in expected_value.items():
                actual_turn = next(turn for turn in actual["turns"] if str(turn["turn"]) == number)
                for turn_field, value in turn_expected.items():
                    assert actual_turn[turn_field] == value, f"{case_id}: turns[{number}].{turn_field}"
        else:
            assert actual[field] == expected_value, f"{case_id}: {field}"


@pytest.mark.parametrize("case", CORE_CASES, ids=lambda case: case["id"])
def test_frozen_core_cases(case: dict) -> None:
    _assert_subset(classify_run(case["run"], case["scene"]), case["expected"], case["id"])


@pytest.mark.parametrize("case_id", EXTENSION_CASES, ids=lambda case_id: f"skipped-extension-{case_id}")
def test_extension_cases_are_deferred(case_id: str) -> None:
    pytest.skip(f"extension-tier case {case_id} is deferred; core contract only")


def _scene(window: int | None = 3) -> dict:
    return {
        "pacing_window": window,
        "terminal": False,
        "reveal_ids": ["reveal"],
        "delivered_before": [],
        "ending_requires": [],
    }


def _turn(number: int, *, outcome: str = "committed", **changes: object) -> dict:
    turn = {
        "turn": number,
        "outcome": outcome,
        "rejected": False,
        "game_break": None,
        "story_complete": False,
        "grounding_ids": [],
        "null_grounding_ids": [],
        "committed_facts": [],
        "candidates_offered": ["reveal"],
        "transition_cause": "none",
    }
    turn.update(changes)
    return turn


def test_does_not_mutate_and_is_deterministic() -> None:
    run = {"entry_facts": [], "turns": [_turn(1, grounding_ids=["g"], committed_facts=[])]}
    scene = _scene()
    original = copy.deepcopy((run, scene))
    first = classify_run(run, scene)
    assert (run, scene) == original
    assert first == classify_run(run, scene)


def test_empty_and_malformed_inputs_are_safe_and_unresolved() -> None:
    assert classify_run({"turns": []}, {})["exit"] == "none"
    assert classify_run({"turns": []}, {})["status"] == "healthy"
    malformed = [
        {"turns": "bad"},
        {"turns": ["bad"]},
        {"turns": [_turn(1, grounding_ids="bad")]},
        {"turns": [_turn(1, **{"turn": None})]},
    ]
    for run in malformed:
        result = classify_run(run, _scene())
        assert result["unresolved"], run


def test_saved_report_shape_has_unknown_telemetry() -> None:
    turn = _turn(1)
    del turn["committed_facts"]
    del turn["null_grounding_ids"]
    result = classify_run({"turns": [turn]}, _scene())
    assert result["turns"][0]["action_outcome"] == "unknown_telemetry"
    assert result["unresolved"] == [1]


def test_rejected_turn_does_not_break_stall() -> None:
    turns = [_turn(1), _turn(2, outcome="rejected", rejected=True), _turn(3), _turn(4)]
    result = classify_run({"turns": turns}, _scene(3))
    assert result["confirmed_stuck"] == [1, 3, 4]


def test_separate_stalls_are_judged_independently() -> None:
    turns = [_turn(1), _turn(2), _turn(3, committed_facts=["changed"]), _turn(4), _turn(5), _turn(6)]
    result = classify_run({"turns": turns}, _scene(2))
    assert result["confirmed_stuck"] == [1, 2, 4, 5, 6]


def test_window_boundary() -> None:
    assert classify_run({"turns": [_turn(1), _turn(2)]}, _scene(2))["confirmed_stuck"] == [1, 2]
    assert classify_run({"turns": [_turn(1)]}, _scene(2))["confirmed_stuck"] == []
