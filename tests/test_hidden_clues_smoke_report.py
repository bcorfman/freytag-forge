from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.ringer.environment_narration import hidden_clues_smoke_report as report


def _world(parent: str, hidden: bool) -> dict[str, dict[str, object]]:
    return {
        clue: {
            "parent": parent,
            "relation": "carried_by" if parent == "kristin" else "under",
            "hidden": hidden,
            "axes": {},
        }
        for clue in report.CLUES
    }


def _turn(command: str, index: int, *, recovered: bool = False, outcome: str = "committed") -> dict:
    world = _world("kristin", False) if recovered else _world("park_bench", True)
    selected = [report.RECOVERY_KNOWLEDGE] if recovered else []
    return {
        "route": report.ROUTE,
        "input": command,
        "turn_index": index + 10,
        "selected_knowledge_ids": selected,
        "narration": "The scene continues.",
        "error": None,
        "turn_outcome": outcome,
        "world_before": world,
        "world_after": world,
        "state_digest_before": f"before-{index}",
        "state_digest_after": f"after-{index}",
        "state_unchanged": False,
        "story_facts_after": {report.RECOVERY_FACT: recovered},
        "narration_attempts": 1,
        "verifier_requests": 0,
        "verifier_http_calls": 0,
        "turn_elapsed_s": 1.0,
        "prompts": [{"user": "The bench is ordinary."}],
        "provider_responses": [],
        "engine_steps": {},
    }


def _replicate(*, recovered: bool = True) -> dict:
    turns = [_turn(command, index, recovered=recovered and index == 1) for index, command in enumerate(report.COMMANDS)]
    turns[1]["narration"] = "Kristin retrieves the three objects." if recovered else None
    turns[1]["turn_outcome"] = "committed" if recovered else "rejected"
    if not recovered:
        turns[1]["state_digest_after"] = turns[1]["state_digest_before"]
        turns[1]["state_unchanged"] = True
    for index in range(2, 6):
        turns[index]["world_before"] = turns[index - 1]["world_after"]
        turns[index]["world_after"] = (
            copy.deepcopy(turns[1]["world_after"]) if recovered else turns[index]["world_after"]
        )
    return {
        "route": report.ROUTE,
        "opening": {
            "narration": "The park is quiet.",
            "prompts": [{"user": "The ordinary bench is nearby."}],
            "provider_responses": [],
            "engine_steps": {},
        },
        "turns": turns,
    }


def _write_run(
    tmp_path: Path,
    rows: list[dict],
    *,
    requested: object = 3,
    stopped: object = None,
) -> Path:
    rows_dir = tmp_path / "rows"
    rows_dir.mkdir()
    (rows_dir / "rows.json").write_text(json.dumps(rows), encoding="utf-8")
    (rows_dir / "summary.json").write_text(
        json.dumps(
            {
                "route": report.ROUTE,
                **({"replicates_requested": requested} if requested is not None else {}),
                "replicates_completed": len(rows),
                "turns_recorded": sum(len(row["turns"]) for row in rows),
                "stopped_reason": stopped,
            }
        ),
        encoding="utf-8",
    )
    return rows_dir


def _passing_rows(count: int = 3) -> list[dict]:
    return [_replicate() for _ in range(count)]


def test_fully_passing_replicates_report_all_gates(tmp_path: Path, capsys) -> None:
    rows_dir = _write_run(tmp_path, _passing_rows())

    assert report.main([str(rows_dir)]) == 0
    output = capsys.readouterr().out
    assert all(f"S{number}: PASS" in output for number in range(1, 7))
    assert "S6 note: item-facts and shared-recovery request counts are not recorded" in output
    assert "run: complete" in output


def test_s1_fails_when_find_does_not_commit(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    rows[0]["turns"][1]["turn_outcome"] = "rejected"
    rows[0]["turns"][1]["narration"] = None
    rows[0]["turns"][1]["selected_knowledge_ids"] = []
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 1
    assert "S1: FAIL" in capsys.readouterr().out


def test_s1_does_not_accept_selected_recovery_without_fact(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    rows[0]["turns"][1]["story_facts_after"] = {}
    rows[0]["turns"][1]["selected_knowledge_ids"] = [report.RECOVERY_KNOWLEDGE]
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 1
    assert "S1: FAIL" in capsys.readouterr().out


def test_s6_is_insufficient_when_budget_fields_are_missing(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    del rows[0]["turns"][2]["narration_attempts"]
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 1
    assert "S6: insufficient evidence" in capsys.readouterr().out


def test_s6_fails_for_an_over_budget_turn(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    rows[0]["turns"][2]["narration_attempts"] = 3
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 1
    assert "S6: FAIL" in capsys.readouterr().out


def test_s2_fails_for_a_clue_name_in_opening(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    rows[0]["opening"]["narration"] = "A transit token glints."
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 1
    assert "S2: FAIL" in capsys.readouterr().out


def test_s3_fails_for_a_second_recovery(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    rows[0]["turns"][4]["selected_knowledge_ids"] = [report.RECOVERY_KNOWLEDGE]
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 1
    assert "S3: FAIL" in capsys.readouterr().out


def test_s3_persistent_recovery_fact_is_one_transition(tmp_path: Path, capsys) -> None:
    rows_dir = _write_run(tmp_path, _passing_rows())

    assert report.main([str(rows_dir)]) == 0
    assert "S3: PASS" in capsys.readouterr().out


def test_s4_fails_for_a_face_fact_at_the_find(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    rows[0]["turns"][1]["selected_knowledge_ids"] = ["k_sl_1b_a_r2"]
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 1
    assert "S4: FAIL" in capsys.readouterr().out


def test_s5_fails_for_a_rejected_turn_that_changed_digest(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    rejected = rows[0]["turns"][2]
    rejected["turn_outcome"] = "rejected"
    rejected["narration"] = None
    rejected["state_digest_before"] = "same"
    rejected["state_digest_after"] = "different"
    rejected["state_unchanged"] = False
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 1
    assert "S5: FAIL" in capsys.readouterr().out


def test_call_cap_exception_is_reported_but_not_ordinary_rejection(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    cap = rows[0]["turns"][2]
    cap["turn_outcome"] = "stopped_call_cap"
    cap["narration"] = None
    cap["error"] = "CallCapExceeded: max-calls exceeded"
    cap["state_unchanged"] = False
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 0
    output = capsys.readouterr().out
    assert "S5: PASS" in output
    assert "call-cap exceptions" in output
    assert "r0t2" in output


def test_drain_rejection_is_excluded_from_s5(tmp_path: Path, capsys) -> None:
    rows = _passing_rows()
    drain = rows[0]["turns"][5]
    drain["turn_outcome"] = "rejected"
    drain["narration"] = None
    drain["state_unchanged"] = False
    drain["state_digest_before"] = "changed"
    drain["state_digest_after"] = "again"
    drain["world_after"]["transit_card"]["parent"] = "park_bench"
    drain["world_after"]["transit_card"]["hidden"] = True
    rows_dir = _write_run(tmp_path, rows)

    assert report.main([str(rows_dir)]) == 0
    output = capsys.readouterr().out
    assert "S5: PASS" in output
    assert "drain outcomes (turn 5; excluded from S1-S6):" in output
    assert "r0t5: outcome=rejected" in output
    assert "r1t5: outcome=committed" in output


def test_incomplete_run_fails_even_when_available_rows_pass(tmp_path: Path, capsys) -> None:
    rows_dir = _write_run(tmp_path, _passing_rows()[:2], stopped="MAX_CALLS_EXCEEDED")

    assert report.main([str(rows_dir)]) == 1
    output = capsys.readouterr().out
    assert "run: incomplete or stopped" in output


def test_expected_replicates_controls_five_replicate_completeness(tmp_path: Path, capsys) -> None:
    rows_dir = _write_run(tmp_path, _passing_rows(5), requested=5)

    assert report.main([str(rows_dir)]) == 1
    default_output = capsys.readouterr().out
    assert "replicates: 5/3" in default_output
    assert "rows=5/3" in default_output

    text, passed = report.report(rows_dir, expected_replicates=5)
    assert passed
    assert "replicates: 5/5" in text
    assert "run: complete" in text


def test_missing_requested_replicates_is_insufficient_evidence(tmp_path: Path, capsys) -> None:
    rows_dir = _write_run(tmp_path, _passing_rows(), requested=None)

    assert report.main([str(rows_dir)]) == 1
    output = capsys.readouterr().out
    assert "replicates_requested: insufficient evidence" in output
    assert "run: incomplete or stopped" in output
