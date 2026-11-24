from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from factory.outcome_contract import classify_run

CASES = json.loads((Path(__file__).parent / "fixtures/outcome_contract/cases.json").read_text())


def _assert_subset(actual: dict, expected: dict, case_id: str) -> None:
    for field, expected_value in expected.items():
        if field == "turns":
            for number, turn_expected in expected_value.items():
                actual_turn = next(turn for turn in actual["turns"] if str(turn["turn"]) == number)
                for turn_field, value in turn_expected.items():
                    assert actual_turn[turn_field] == value, f"{case_id}: turns[{number}].{turn_field}"
        else:
            assert actual[field] == expected_value, f"{case_id}: {field}"


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_frozen_cases(case: dict) -> None:
    _assert_subset(classify_run(case["run"], case["scene"]), case["expected"], case["id"])


def test_m4_cases_cover_futile_named_command_and_grounding_rules() -> None:
    cases_by_id = {case["id"]: case for case in CASES}
    m4_ids = {
        "timed_reveal_masks_futile_action",
        "pressure_beside_earned_reveal",
        "pacing_event_caused_by_command_fact",
    }
    assert m4_ids <= cases_by_id.keys()
    timed_turns = cases_by_id["timed_reveal_masks_futile_action"]["run"]["turns"]
    assert all(not turn["input"].startswith("Wait") for turn in timed_turns)


def _scene(window: int | None = 3) -> dict:
    return {
        "pacing_window": window,
        "terminal": False,
        "reveal_ids": ["reveal"],
        "delivered_before": [],
        "ending_requires": [],
    }


def test_provenance_only_checks_independent_quoted_segments_and_curly_quotes() -> None:
    scene = {
        **_scene(),
        "non_voiceable_says": ["internal summary"],
        "unlearned_terms": [{"term": "Phase Two", "requires": "phase_one"}],
    }
    turns = [
        _turn(1, text='Narration says internal summary, but "ordinary" is fine.'),
        _turn(2, text='“Phase Two begins.” Then "internal summary".'),
        _turn(3, text="The narrator says “Phase Two is here."),
        _turn(4),
    ]
    flags = classify_run({"turns": turns}, scene)["provenance_flags"]
    assert flags == [
        {"turn": 2, "kind": "bookkeeping_voiced"},
        {"turn": 2, "kind": "character_knowledge"},
        {"turn": 3, "kind": "character_knowledge"},
    ]


@pytest.mark.parametrize("reset", ["pressure_event", "npc_move", "knowledge_progress"])
def test_quiet_stretch_resets_on_activity(reset: str) -> None:
    turns = [_turn(1, pressure_event=True)]
    for number in range(2, 5):
        changes = {"grounding_ids": [], "committed_facts": []}
        if number == 3:
            if reset == "knowledge_progress":
                changes["grounding_ids"] = ["reveal"]
            else:
                changes[reset] = True
        turns.append(_turn(number, **changes))
    turns.append(_turn(5))
    assert classify_run({"turns": turns}, _scene())["pacing"]["quiet_stretch"] == 2


def test_zero_turn_pacing_and_epilogue_taken_requires_offer() -> None:
    result = classify_run({"turns": []}, {"epilogue_candidates": ["epi"]})
    assert result["pacing"]["exploration_share"] == 0.0
    run = {
        "turns": [
            _turn(1, story_complete=True, ending_latched=True, committed_facts=["done"]),
            _turn(2, matched_candidate="epi"),
        ]
    }
    scene = {**_scene(), "terminal": True, "epilogue_candidates": ["epi"]}
    result = classify_run(run, scene)
    assert result["epilogue"] == {"offered": False, "taken": False}


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
