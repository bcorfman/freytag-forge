from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from factory.contract_scene import build_contract_scene
from factory.outcome_contract import classify_run
from factory.report_telemetry import enrich_report, main
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


def test_attaches_sibling_bundles_by_replicate_and_scene() -> None:
    report = {
        "replicates": [
            {"replicate": 2, "scenes": [{"scene": "3B", "turns": []}]},
            {"replicate": 1, "scene": "3B", "turns": []},
        ]
    }
    bundles = {
        "story_id": "continuity-initiative",
        "scene": "3B",
        "replicates": [
            {"replicate": 1, "scenes": [{"scene": "3B", "bundles": [{"turn": 1}]}]},
            {"replicate": 2, "scenes": [{"scene": "3B", "bundles": [{"turn": 2}]}]},
        ],
    }
    result = enrich_report(report, PACKAGE, bundles_report=bundles)
    assert result["replicates"][0]["scenes"][0]["bundles"] == [{"turn": 2}]
    assert result["replicates"][1]["bundles"] == [{"turn": 1}]


def test_missing_bundle_match_remains_a_gap() -> None:
    report = _report(bundle=False)
    bundles = {"replicates": [{"replicate": 9, "scenes": [{"scene": "2A", "bundles": []}]}]}
    result = enrich_report(report, PACKAGE, bundles_report=bundles)
    assert result["replicates"][0]["telemetry_gaps"] == ["turn 1: missing bundle"]


def test_derives_start_entry_state() -> None:
    report = _report(entry=False)
    report["replicates"][0]["entry"] = {"mode": "start"}
    result = enrich_report(report, PACKAGE, story_root=Path("data/stories/continuity-initiative"))
    run = result["replicates"][0]
    assert run["entry_state"] == {
        "scene_id": "2A",
        "turn_index": 0,
        "fired_pacing_event_ids": [],
    }
    assert run["entry_state_source"] == "derived_start"


def test_derives_seeded_snapshot_entry_state() -> None:
    report = _report(entry=False)
    run = report["replicates"][0]
    run["scene"] = "3B"
    run["entry"] = {"mode": "seeded"}
    result = enrich_report(
        report,
        PACKAGE,
        story_root=Path("data/stories/continuity-initiative"),
    )
    entry = result["replicates"][0]["entry_state"]
    assert entry["turn_index"] == 40
    assert entry["fired_pacing_event_ids"] == [
        "detention_lockdown_3a",
        "home_search_narrows_1a",
        "override_deadline_3a",
        "park_lockdown_1b",
        "patrol_arrives_1a",
        "patrol_enters_1a",
        "patrol_leaves_1a",
        "patrol_returns_1a",
        "pursuit_1b",
    ]
    assert result["replicates"][0]["entry_state_source"] == "derived_snapshot"


def test_unsupported_entry_mode_fails_closed() -> None:
    report = _report(entry=False)
    report["replicates"][0]["entry"] = {"mode": "walk"}
    result = enrich_report(report, PACKAGE, story_root=Path("data/stories/continuity-initiative"))
    assert result["replicates"][0]["telemetry_gaps"] == ["turn 1: missing entry_state"]


def test_reported_entry_state_is_kept_and_labelled() -> None:
    report = _report()
    original_entry = deepcopy(report["replicates"][0]["entry_state"])
    result = enrich_report(
        report,
        PACKAGE,
        story_root=Path("data/stories/continuity-initiative"),
    )
    assert result["replicates"][0]["entry_state"] == original_entry
    assert result["replicates"][0]["entry_state_source"] == "reported"


def test_new_inputs_are_not_mutated() -> None:
    report = _report(bundle=False, entry=False)
    bundles = {"replicates": [{"replicate": 1, "scenes": [{"scene": "2A", "bundles": [{"turn": 1}]}]}]}
    original_report, original_bundles = deepcopy(report), deepcopy(bundles)
    enrich_report(
        report,
        PACKAGE,
        bundles_report=bundles,
        story_root=Path("data/stories/continuity-initiative"),
    )
    assert report == original_report
    assert bundles == original_bundles


def test_old_two_argument_call_matches_explicit_defaults() -> None:
    report = _report()
    assert enrich_report(report, PACKAGE) == enrich_report(report, PACKAGE, bundles_report=None, story_root=None)


def test_cli_returns_one_for_report_with_gaps(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    bundles_path = tmp_path / "bundles.json"
    out_path = tmp_path / "out.json"
    report_path.write_text(json.dumps(_report(bundle=False)))
    bundles_path.write_text(json.dumps({"replicates": []}))
    assert (
        main(
            [
                str(report_path),
                "--bundles",
                str(bundles_path),
                "--story-root",
                "data/stories/continuity-initiative",
                "--out",
                str(out_path),
            ]
        )
        == 1
    )
    assert out_path.exists()


def test_cli_returns_two_for_missing_input(tmp_path: Path) -> None:
    assert (
        main(
            [
                str(tmp_path / "missing.json"),
                "--bundles",
                str(tmp_path / "bundles.json"),
                "--story-root",
                "data/stories/continuity-initiative",
                "--out",
                str(tmp_path / "out.json"),
            ]
        )
        == 2
    )
