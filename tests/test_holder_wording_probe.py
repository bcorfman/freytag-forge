import hashlib
import json
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import holder_wording_probe as probe
from storygame.runtime.observation_verifier import Relation


def _turn(turn_index, *, examine=False):
    holder = f"Holder {turn_index}"
    return {
        "input": "examine my laptop" if examine else "look",
        "narration": f"The narration for turn {turn_index}.",
        "observation_relations": [{"thing": f"thing {turn_index}", "place": holder, "holder": holder}],
        "error": None,
    }


def _rows():
    return [{"turns": [_turn(index, examine=index < 5)]} for index in range(10)]


def _write_rows(path, rows):
    path.write_text(json.dumps(rows), encoding="utf-8")


def _write_cases_and_lock(monkeypatch, tmp_path, cases):
    cases_path = tmp_path / "cases.jsonl"
    data = "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases)
    cases_path.write_text(data, encoding="utf-8")
    lock_path = tmp_path / "cases.lock.json"
    lock_path.write_text(
        json.dumps({"sha256": hashlib.sha256(data.encode()).hexdigest(), "count": len(cases)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(probe, "CASES_PATH", cases_path)
    monkeypatch.setattr(probe, "LOCK_PATH", lock_path)


def test_build_cases_counts_and_fields(tmp_path):
    rows_path = tmp_path / "rows.json"
    _write_rows(rows_path, _rows())

    cases = probe.build_cases(rows_path)

    assert len(cases) == 25
    assert [case["kind"] for case in cases[:3]] == ["absent_thing", "positive_held", "wrong_holder"]
    assert all(set(case) == {"id", "kind", "label", "narration", "relation", "source_turn"} for case in cases)
    assert sum(case["kind"] == "positive_held" for case in cases) == 10
    assert sum(case["kind"] == "wrong_holder" for case in cases) == 10
    assert sum(case["kind"] == "absent_thing" for case in cases) == 5
    assert cases[0]["id"] == "h-a-r0t0"
    assert cases[-1]["id"] == "h-w-r9t0"
    absent = [case for case in cases if case["kind"] == "absent_thing"]
    assert absent[0]["relation"] == {
        "thing": "Michelle's memory card",
        "place": "Kristin Schweitzer",
        "holder": "Kristin Schweitzer",
    }


def test_build_cases_rejects_wrong_holder_count(tmp_path):
    rows_path = tmp_path / "rows.json"
    _write_rows(rows_path, _rows()[:1])

    with pytest.raises(ValueError) as error:
        probe.build_cases(rows_path)
    assert "exactly 10" in str(error.value)


def test_held_only_normalization_and_questions():
    held = Relation("laptop", "Michelle McGehee", "Michelle McGehee")
    other = Relation("book", "desk", "Michelle McGehee")
    bare = Relation("coin", None, "Michelle McGehee")

    assert probe.held_only_relation(held) == Relation("laptop", None, "Michelle McGehee")
    assert probe.held_only_relation(other) == other
    assert probe.held_only_relation(bare) == bare
    assert probe.question_for_arm(held, "current") != probe.question_for_arm(held, "held_only")
    assert probe.question_for_arm(other, "current") == probe.question_for_arm(other, "held_only")


def test_check_corpus_reports_zero_changed(capsys):
    assert probe.main(["--check-corpus"]) == 0
    output = capsys.readouterr().out
    assert "changed questions: 0" in output
    assert "relations examined:" in output


def test_dry_run_numbers(capsys):
    assert probe.main(["--dry-run", "--samples", "2"]) == 0
    output = capsys.readouterr().out
    assert "case count: 25" in output
    assert "planned requests: 100" in output
    assert "token estimate:" in output
    assert "USD ceiling:" in output


@pytest.mark.parametrize(
    "arguments, expected",
    [
        (["--run"], "requires --confirm"),
        (["--run", "--confirm", "--max-calls", "1"], "exceed --max-calls"),
        (["--run", "--confirm", "--max-usd", "0"], "exceeds --max-usd"),
    ],
)
def test_run_mode_refusals(monkeypatch, tmp_path, capsys, arguments, expected):
    cases = probe.build_cases(
        Path("/home/bcorfman/dev/freytag-forge/bench/results/environment-narration/shadow-sample/full/rows/rows.json")
    )
    _write_cases_and_lock(monkeypatch, tmp_path, cases)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)

    assert probe.main(arguments + ["--out", str(tmp_path / "rows.json")]) == 2
    assert expected in capsys.readouterr().err


def test_run_refuses_lock_mismatch(monkeypatch, tmp_path, capsys):
    cases = probe.build_cases(
        Path("/home/bcorfman/dev/freytag-forge/bench/results/environment-narration/shadow-sample/full/rows/rows.json")
    )
    _write_cases_and_lock(monkeypatch, tmp_path, cases)
    monkeypatch.setattr(probe, "LOCK_PATH", tmp_path / "wrong.lock.json")
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "do-not-print-this-token")

    assert probe.main(["--run", "--confirm", "--out", str(tmp_path / "rows.json")]) == 2
    assert "matching lock" in capsys.readouterr().err


def test_run_refuses_missing_environment(monkeypatch, tmp_path, capsys):
    cases = probe.build_cases(
        Path("/home/bcorfman/dev/freytag-forge/bench/results/environment-narration/shadow-sample/full/rows/rows.json")
    )
    _write_cases_and_lock(monkeypatch, tmp_path, cases)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)

    assert probe.main(["--run", "--confirm", "--out", str(tmp_path / "rows.json")]) == 2
    assert "CLOUDFLARE_WORKER_URL" in capsys.readouterr().err


class FakeClient:
    last_model = "fake-model"
    last_status = 200

    def __init__(self):
        self.calls = []

    def ask(self, state, questions):
        self.calls.append((state, questions))
        return {key: {"noul": 0.9} for key in questions}


def test_run_writes_interleaved_rows(monkeypatch, tmp_path):
    cases = probe.build_cases(
        Path("/home/bcorfman/dev/freytag-forge/bench/results/environment-narration/shadow-sample/full/rows/rows.json")
    )
    client = FakeClient()
    output = tmp_path / "run.json"

    document = probe.run_cases(cases, samples=2, max_calls=100, out=output, client=client)

    assert len(document["rows"]) == 100
    assert [row["arm"] for row in document["rows"][:4]] == ["current", "held_only", "current", "held_only"]
    assert all(
        set(row)
        >= {
            "case_id",
            "kind",
            "label",
            "arm",
            "sample",
            "verdict",
            "score",
            "outcome",
            "failure",
            "latency_ms",
            "jev_model",
            "question_text_hash",
        }
        for row in document["rows"]
    )
    assert output.exists()
    assert len(client.calls) == 100


def _report_rows():
    rows = []
    for arm in ("current", "held_only"):
        cases = [("positive_held", "accept", "accept", 20)]
        cases.extend(
            [
                ("wrong_holder", "reject", "reject", 15),
                ("absent_thing", "reject", "reject", 15),
            ]
        )
        for kind, label, verdict, sample_count in cases:
            for sample in range(sample_count):
                rows.append(
                    {
                        "case_id": f"{kind}-{arm}-{sample}",
                        "kind": kind,
                        "label": label,
                        "arm": arm,
                        "sample": sample,
                        "verdict": verdict,
                        "score": 0.9 if verdict == "accept" else 0.1,
                        "outcome": "ok",
                    }
                )
    return rows


def test_report_gate_pass_and_fail(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": _report_rows()}), encoding="utf-8")

    assert probe.report_rows(rows_path, report_path) == 0
    report = report_path.read_text(encoding="utf-8")
    assert "G1" in report and "G1: PASS" in report
    assert "G2: PASS" in report and "G3: PASS" in report
    assert "10 positive cases are the ones that exposed the defect" in report

    rows = _report_rows()
    rows[50]["verdict"] = "reject"
    rows[51]["verdict"] = "reject"
    rows[52]["verdict"] = "reject"
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path) == 1
    report = report_path.read_text(encoding="utf-8")
    assert "G1: FAIL" in report
    assert "G3: FAIL" in report


def test_no_credential_value_in_output(monkeypatch, tmp_path, capsys):
    secret = "super-secret-holder-probe-token"
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", secret)
    assert probe.main(["--dry-run", "--samples", "1"]) == 0
    assert secret not in capsys.readouterr().out
