import hashlib
import json
from pathlib import Path

from scripts.ringer.environment_narration import make_t9b_probe_run_manifest as manifest
from scripts.ringer.environment_narration import under_question_probe as probe

PREREG = Path(__file__).parents[1] / ".plans/grounded-llm-environment-narration/t9b-scope-prereg.md"


def _cases_and_lock(monkeypatch, tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    data = probe._cases_bytes(probe.FROZEN_CASES)
    cases_path.write_bytes(data)
    lock_path = tmp_path / "cases.lock.json"
    lock_path.write_text(
        json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "count": len(probe.FROZEN_CASES)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(probe, "CASES_PATH", cases_path)
    monkeypatch.setattr(probe, "LOCK_PATH", lock_path)
    return cases_path, lock_path


def _rows_for_report(returned=True):
    rows = []
    for case in probe.FROZEN_CASES:
        for sample in range(2):
            answer = returned if case["expected"] else not returned
            rows.append(
                {
                    "case_id": case["id"],
                    "sample": sample,
                    "returned": answer,
                    "noul": 0.9 if answer else 0.1,
                    "raw_answer": {"searches_underneath": {"noul": 0.9 if answer else 0.1}},
                    "jev_model": "fake-model",
                }
            )
    return rows


def test_frozen_corpus_matches_prereg_and_has_expected_shape():
    cases = probe._load_cases()
    prereg = PREREG.read_text(encoding="utf-8")

    assert len(cases) == 49
    assert sum(case["expected"] for case in cases) == 20
    assert sum(not case["expected"] for case in cases) == 29
    assert len({case["id"] for case in cases}) == 49
    assert [case["id"] for case in cases[:20]] == [f"u-p{index:02d}" for index in range(1, 21)]
    assert [case["id"] for case in cases[20:]] == [f"u-n{index:02d}" for index in range(1, 30)]
    assert sum(case.get("hard", False) for case in cases) == 2
    assert all(case["command"] in prereg for case in cases)


def test_lock_matches_and_modified_case_fails_check(monkeypatch, tmp_path, capsys):
    cases_path, _ = _cases_and_lock(monkeypatch, tmp_path)
    assert probe.main(["--check-corpus"]) == 0
    cases_path.write_text(
        cases_path.read_text(encoding="utf-8").replace("Feel under the drawer.", "Feel beside the drawer."),
        encoding="utf-8",
    )

    assert probe.main(["--check-corpus"]) == 1
    assert "lock" in capsys.readouterr().out


def test_run_without_confirm_makes_no_call(monkeypatch, tmp_path):
    calls = []

    class NoCallClient:
        @classmethod
        def from_environment(cls):
            calls.append("constructed")
            return cls()

    monkeypatch.setattr(probe, "JevClient", NoCallClient)
    assert probe.main(["--run", "--out", str(tmp_path / "rows.json")]) != 0
    assert calls == []


class FakeClient:
    last_model = "fake-model"
    last_status = 200

    def __init__(self):
        self.calls = []

    def ask(self, state, questions):
        self.calls.append((state, questions))
        return {"searches_underneath": {"noul": 0.9}}


def test_capped_run_records_answers_scores_and_stop_reason(tmp_path):
    client = FakeClient()
    output = tmp_path / "rows.json"

    document = probe.run_cases(list(probe.FROZEN_CASES), samples=2, max_calls=98, out=output, client=client)

    assert len(document["rows"]) == 98
    assert document["stop_reason"] == "max_calls"
    assert len(client.calls) == 98
    assert all(row["returned"] is True and row["noul"] == 0.9 for row in document["rows"])
    assert all("raw_answer" in row and row["jev_model"] == "fake-model" for row in document["rows"])


def test_report_j1_j2_nulls_and_missed_cases(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows = _rows_for_report()
    rows[0]["returned"] = None
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")

    assert probe.report_rows(rows_path, report_path) == 0
    report = report_path.read_text(encoding="utf-8")
    assert "J1: PASS" in report and "J2: PASS" in report
    assert "null answers: 1" in report
    assert "probe gate: PASS" in report

    negative = next(row for row in rows if row["case_id"] == "u-n01")
    negative["returned"] = True
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path) == 1
    assert "J1: FAIL" in report_path.read_text(encoding="utf-8")

    rows = _rows_for_report()
    positive_rows = [row for row in rows if row["case_id"] == "u-p01"]
    for row in positive_rows:
        row["returned"] = False
    for case_id in ("u-p02", "u-p03", "u-p04"):
        for row in rows:
            if row["case_id"] == case_id:
                row["returned"] = False
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path) == 1
    report = report_path.read_text(encoding="utf-8")
    assert "J2: FAIL" in report
    assert "u-p01" in report and "u-p04" in report


def test_dry_run_prints_98_and_does_not_construct_client(monkeypatch, capsys):
    calls = []

    class NoCallClient:
        @classmethod
        def from_environment(cls):
            calls.append("constructed")
            return cls()

    monkeypatch.setattr(probe, "JevClient", NoCallClient)
    assert probe.main(["--dry-run"]) == 0
    assert "98" in capsys.readouterr().out
    assert calls == []


def test_manifest_is_generated_and_contains_probe_guards(tmp_path):
    output_dir = tmp_path / "manifests"
    manifest.main(output_dir)
    generated = json.loads((output_dir / "run-t9b-probe-live.json").read_text(encoding="utf-8"))
    committed = json.loads(
        (Path(__file__).parents[1] / "scripts/ringer/environment_narration/run-t9b-probe-live.json").read_text(
            encoding="utf-8"
        )
    )

    assert generated == committed
    task = generated["tasks"][0]
    assert "--max-calls 98" in task["spec"]
    assert "--max-usd 0.01" in task["spec"]
    assert "98" in task["check"]
    assert "probe gate" in task["check"]
