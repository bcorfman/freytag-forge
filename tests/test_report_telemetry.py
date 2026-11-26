from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from factory.contract_scene import build_contract_scene
from factory.outcome_contract import classify_run
from factory.report_telemetry import enrich_report
from factory.turn_telemetry import pacing_effects_by_event
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _bundle(**updates: object) -> dict:
    bundle = {
        "outcome": "committed",
        "story_complete": False,
        "transition_cause": "none",
        "committed_delta": {"fact_predicates": ["command_fact"]},
        "reveal_selection": {"shortlist_ids": [], "matched": None},
    }
    bundle.update(updates)
    return bundle


def _report(*, replay: bool = True, bundle: bool = True, entry: bool = True) -> dict:
    turn = {
        "turn": 1,
        "raw_input": "Wait.",
        "text": "Nothing changes.",
        "outcome": "committed",
        "grounding_ids": [],
        "pacing_replay": {"fired_event_ids": [], "null_grounding_ids": []} if replay else None,
        "fired_pacing_event_ids": [],
    }
    run = {"replicate": 1, "scene": "2A", "turns": [turn]}
    if bundle:
        run["bundles"] = [{"turn": 1, "attempt_bundle": _bundle()}]
    if entry:
        run["entry_state"] = {"scene_id": "2A", "fired_pacing_event_ids": []}
    return {"replicates": [run]}


def test_enriches_without_mutating_and_is_deterministic() -> None:
    report = _report()
    original = deepcopy(report)
    first = enrich_report(report, PACKAGE)
    second = enrich_report(report, PACKAGE)
    assert report == original
    assert first == second
    assert first["replicates"][0]["turns"][0]["committed_facts"] == ["command_fact"]


def test_nested_scene_and_rejected_without_bundle() -> None:
    report = _report()
    run = report["replicates"][0]
    nested = {"scene": "2A", "turns": [{"turn": 1, "outcome": "rejected", "text": "No."}]}
    report = {"replicates": [{"replicate": 1, "scenes": [run, nested]}]}
    result = enrich_report(report, PACKAGE)
    assert "committed_facts" in result["replicates"][0]["scenes"][0]["turns"][0]
    assert result["replicates"][0]["scenes"][1]["turns"][0]["committed_facts"] == []


def test_fail_closed_records_gap_and_classification_is_unresolved() -> None:
    for kwargs, gap in [
        ({"replay": False}, "pacing_replay"),
        ({"bundle": False}, "bundle"),
        ({"entry": False}, "entry_state"),
    ]:
        result = enrich_report(_report(**kwargs), PACKAGE)
        run = result["replicates"][0]
        assert run["telemetry_gaps"] == [f"turn 1: missing {gap}"]
        assert "committed_facts" not in run["turns"][0]
        assert classify_run(run, build_contract_scene(PACKAGE, "2A"))["status"] == "unresolved"


def test_pacing_effect_lookup_is_available_for_real_package() -> None:
    assert pacing_effects_by_event(PACKAGE)
