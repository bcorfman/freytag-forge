import json

import pytest

from scripts.ringer.environment_narration import enforce_report


def _relation(thing="brass marker", place="shelf", holder="room"):
    return {"thing": thing, "place": place, "holder": holder}


def _attempt(*, accepted=True, narration="The marker rests on the shelf.", relations=None):
    return {
        "narration": narration,
        "relations": [_relation()] if relations is None else relations,
        "outcome": "accepted" if accepted else "rejected",
        "accepted": accepted,
        "verdicts": [],
        "requests": 1,
        "failure": None,
        "elapsed_s": 0.2,
    }


def _turn(
    command="inspect the alcove",
    *,
    narration="The marker rests on the shelf.",
    attempts=1,
    verifier_requests=1,
    enforce_attempts=None,
    error=None,
    elapsed=1.0,
    observation=True,
    places_before=None,
    places_after=None,
    diverged=False,
    provider_responses=None,
):
    if enforce_attempts is None:
        enforce_attempts = [_attempt()]
    if places_before is None:
        places_before = {"player": "room"}
    if places_after is None:
        places_after = {"player": "room"}
    return {
        "input": command,
        "narration": narration,
        "error": error,
        "places_before": places_before,
        "places_after": places_after,
        "narration_attempts": attempts,
        "verifier_requests": verifier_requests,
        "observation_enforce": {"observation_diverged": diverged} if observation else None,
        "enforce_attempts": enforce_attempts if observation else [],
        "provider_responses": provider_responses or [],
        "turn_elapsed_s": elapsed,
    }


def _write_json(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _run(capsys, argv):
    result = enforce_report.main(argv)
    captured = capsys.readouterr()
    return result, captured.out, captured.err


def _labels(rows, *, tag=None, presents=True, earlier=None):
    result = {}
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(replicate["turns"]):
            turn_id = f"r{replicate_index}t{turn_index}"
            rejected = sum(not attempt.get("accepted", False) for attempt in turn.get("enforce_attempts", []))
            extra = max(0, turn.get("narration_attempts", 0) - len(turn.get("enforce_attempts", [])))
            earlier_values = [True] * (rejected + extra) if earlier is None else list(earlier)
            result[turn_id] = {
                "presents_required": presents if turn.get("narration") is not None else None,
                "acceptable": True if turn.get("narration") is not None else None,
                "tags": {
                    "refind": None,
                    "invented_object": None,
                    "leak": None,
                    "wrong_custody": None,
                    "unrequested_move": None,
                },
                "earlier": earlier_values,
            }
            if tag is not None:
                result[turn_id]["tags"][tag] = True
    return result


def _rows_path(tmp_path, rows):
    return _write_json(tmp_path, "rows.json", rows)


def _labels_path(tmp_path, labels):
    return _write_json(tmp_path, "labels.json", labels)


def _clean_rows(count=20):
    return [
        {"route": "observe_topup", "opening": {}, "turns": [_turn(command=f"inspect place {i}") for i in range(count)]}
    ]


def test_clean_run_passes(tmp_path, capsys):
    rows = _clean_rows()
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, _labels(rows)))],
    )

    assert code == 0
    assert error == ""
    assert "enforcement screen: PASS" in output
    assert "Clause 6: PASS" in output


@pytest.mark.parametrize("changed", [False, True])
def test_failed_turn_rollback_clause(tmp_path, capsys, changed):
    before = {"player": "room", "card": "drawer"}
    after = {"player": "room", "card": "outside"} if changed else before
    turn = _turn(
        narration=None,
        attempts=2,
        verifier_requests=2,
        enforce_attempts=[_attempt(accepted=False)],
        error="verification exhausted",
        places_before=before,
        places_after=after,
    )
    rows = [{"turns": [turn]}]
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, _labels(rows)))],
    )

    assert code == 0
    assert error == ""
    assert f"Clause 4: {'FAIL' if changed else 'PASS'}" in output


def test_recovery_is_blindly_shown_and_counted(tmp_path, capsys):
    recovered = _turn(
        attempts=2,
        enforce_attempts=[_attempt(accepted=False, narration="The marker is missing."), _attempt()],
    )
    rows = [{"turns": [recovered]}]
    rows_path = _rows_path(tmp_path, rows)
    labels = _labels(rows)
    labels["r0t0"]["earlier"] = [False]
    labels_path = _labels_path(tmp_path, labels)

    sheet_code, sheet, sheet_error = _run(capsys, ["sheet", str(rows_path)])
    join_code, report, join_error = _run(capsys, ["join", str(rows_path), "--labels", str(labels_path)])

    assert sheet_code == 0
    assert sheet_error == ""
    assert "earlier attempt 1" in sheet
    assert "The marker is missing." in sheet
    assert join_code == 0
    assert join_error == ""
    assert "recovery success rate: 1/1" in report


def test_sheet_leaks_no_verifier_details(tmp_path, capsys):
    turn = _turn(
        attempts=2,
        enforce_attempts=[
            {
                **_attempt(accepted=False, narration="The marker is missing."),
                "outcome": "reject",
                "verdicts": [{"thing": "marker", "score": 0.1, "verdict": "reject"}],
                "requests": 2,
            },
            _attempt(),
        ],
    )
    rows_path = _rows_path(tmp_path, [{"turns": [turn]}])
    code, sheet, error = _run(capsys, ["sheet", str(rows_path)])

    assert code == 0
    assert error == ""
    lowered = sheet.casefold()
    for forbidden in ("score", "verdict", "outcome", "accepted", "request count", "attempt count", "error", "enforce"):
        assert forbidden not in lowered


def test_shuffle_is_deterministic_and_seed_is_printed(tmp_path, capsys):
    rows = _clean_rows(6)
    rows_path = _rows_path(tmp_path, rows)
    first_code, first, first_error = _run(capsys, ["sheet", str(rows_path)])
    second_code, second, second_error = _run(capsys, ["sheet", str(rows_path)])
    ids = [f"r0t{i}" for i in range(6)]
    first_order = [line[3:] for line in first.splitlines() if line.startswith("## r")]

    assert first_code == second_code == 0
    assert first_error == second_error == ""
    assert first == second
    assert "Shuffle seed:" in first
    assert first_order != ids


def test_labels_template_has_required_shape_and_earlier_size(tmp_path, capsys):
    rows = [{"turns": [_turn(), _turn(attempts=2, enforce_attempts=[_attempt(accepted=False)])]}]
    code, output, error = _run(capsys, ["labels-template", str(_rows_path(tmp_path, rows))])

    assert code == 0
    assert error == ""
    assert json.loads(output) == {
        "r0t0": {
            "presents_required": None,
            "acceptable": None,
            "tags": {
                "refind": None,
                "invented_object": None,
                "leak": None,
                "wrong_custody": None,
                "unrequested_move": None,
            },
            "earlier": [],
        },
        "r0t1": {
            "presents_required": None,
            "acceptable": None,
            "tags": {
                "refind": None,
                "invented_object": None,
                "leak": None,
                "wrong_custody": None,
                "unrequested_move": None,
            },
            "earlier": [None],
        },
    }


def test_missing_labels_exit_one(tmp_path, capsys):
    rows = _clean_rows(1)
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, {}))],
    )

    assert code == 1
    assert output == ""
    assert "MISSING LABELS" in error
    assert "r0t0" in error


def test_clause_one_fails_with_two_failed_observations(tmp_path, capsys):
    failed = _turn(narration=None, attempts=2, enforce_attempts=[_attempt(accepted=False)], error="failed")
    rows = [{"turns": [failed, failed]}]
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, _labels(rows)))],
    )

    assert code == 0
    assert error == ""
    assert "Clause 1: FAIL" in output
    assert "2/2" in output


def test_clause_two_fails_and_stops(tmp_path, capsys):
    rows = _clean_rows(1)
    labels = _labels(rows, presents=False)
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, labels))],
    )

    assert code == 0
    assert error == ""
    assert "Clause 2: FAIL" in output
    assert "STOP: the verifier let deficient prose through" in output


@pytest.mark.parametrize("tag", ["leak", "wrong_custody", "unrequested_move"])
def test_clause_three_zero_tolerance_tags_fail(tmp_path, capsys, tag):
    rows = _clean_rows(1)
    labels = _labels(rows, tag=tag)
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, labels))],
    )

    assert code == 0
    assert error == ""
    assert f"{tag}: FAIL" in output


@pytest.mark.parametrize("tag", ["refind", "invented_object"])
def test_clause_three_one_allowed_tag_limit_fails_at_two(tmp_path, capsys, tag):
    rows = _clean_rows(2)
    labels = _labels(rows)
    for turn_labels in labels.values():
        turn_labels["tags"][tag] = True
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, labels))],
    )

    assert code == 0
    assert error == ""
    assert f"{tag}: FAIL" in output


def test_clause_five_fails_over_budget(tmp_path, capsys):
    rows = [{"turns": [_turn(attempts=3, verifier_requests=3)]}]
    labels = _labels(rows)
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, labels))],
    )

    assert code == 0
    assert error == ""
    assert "Clause 5: FAIL" in output


def test_clause_six_fails_with_twenty_slow_turns(tmp_path, capsys):
    rows = _clean_rows(20)
    for turn in rows[0]["turns"]:
        turn["turn_elapsed_s"] = 11.0
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, _labels(rows)))],
    )

    assert code == 0
    assert error == ""
    assert "Clause 6: FAIL" in output
    assert "p95=11.000" in output


def test_clause_six_is_inconclusive_with_fewer_than_twenty_turns(tmp_path, capsys):
    rows = _clean_rows(2)
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, _labels(rows)))],
    )

    assert code == 0
    assert error == ""
    assert "Clause 6: INCONCLUSIVE" in output


def test_clause_seven_fails_with_two_false_reject_labels(tmp_path, capsys):
    turns = [_turn(attempts=2, enforce_attempts=[_attempt(accepted=False)]) for _ in range(5)]
    rows = [{"turns": turns}]
    labels = _labels(rows)
    for index, turn_labels in enumerate(labels.values()):
        turn_labels["earlier"] = [index >= 2]
    code, output, error = _run(
        capsys,
        ["join", str(_rows_path(tmp_path, rows)), "--labels", str(_labels_path(tmp_path, labels))],
    )

    assert code == 0
    assert error == ""
    assert "Clause 7: FAIL" in output
    assert "false rejects: 2" in output


def test_hashes_and_information_lines_are_printed(tmp_path, capsys):
    rows = _clean_rows(1)
    rows[0]["turns"][0]["observation_enforce"] = {"observation_diverged": True}
    rows_path = _rows_path(tmp_path, rows)
    labels_path = _labels_path(tmp_path, _labels(rows))
    code, output, error = _run(capsys, ["join", str(rows_path), "--labels", str(labels_path)])

    assert code == 0
    assert error == ""
    assert "rows sha256:" in output
    assert "labels sha256:" in output
    assert "first-attempt rejection rate:" in output
    assert "total narration attempts:" in output
    assert "total verifier requests:" in output
    assert "mean observation turn elapsed_s:" in output
    assert "observation diverged share:" in output


def test_cli_out_writes_sheet_and_report(tmp_path, capsys):
    rows = _clean_rows(1)
    rows_path = _rows_path(tmp_path, rows)
    labels_path = _labels_path(tmp_path, _labels(rows))
    sheet_path = tmp_path / "sheet.md"
    report_path = tmp_path / "report.md"

    sheet_code, sheet_output, sheet_error = _run(capsys, ["sheet", str(rows_path), "--out", str(sheet_path)])
    report_code, report_output, report_error = _run(
        capsys,
        ["join", str(rows_path), "--labels", str(labels_path), "--out", str(report_path)],
    )

    assert sheet_code == report_code == 0
    assert sheet_output == report_output == ""
    assert sheet_error == report_error == ""
    assert "Blind observation sheet" in sheet_path.read_text(encoding="utf-8")
    assert "enforcement screen" in report_path.read_text(encoding="utf-8")
