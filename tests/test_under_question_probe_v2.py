import hashlib
import json
from pathlib import Path

from scripts.ringer.environment_narration import make_t9b_probe2_run_manifest as manifest
from scripts.ringer.environment_narration import under_question_probe as probe

ROOT = Path(__file__).parents[1]
PREREG = ROOT / ".plans/grounded-llm-environment-narration/t9b-probe2-prereg.md"
V1_CASES = ROOT / "scripts/ringer/environment_narration/under_probe/cases.jsonl"
V1_LOCK = ROOT / "scripts/ringer/environment_narration/under_probe/cases.lock.json"


def _v2_cases():
    return probe._load_cases(corpus="v2")


def _rows_for_v2():
    rows = []
    for case in _v2_cases():
        returned = case["expected"]
        if case["kind"] == "regression":
            returned = False
        for sample in range(2):
            score = 0.9 if returned else 0.1
            rows.append(
                {
                    "case_id": case["id"],
                    "sample": sample,
                    "returned": returned,
                    "noul": score,
                    "score": score,
                }
            )
    return rows


def test_v2_corpus_shape_and_hard_negatives():
    cases = _v2_cases()

    assert len(cases) == 64
    assert sum(case["kind"] == "fresh" and case["expected"] for case in cases) == 24
    assert sum(case["kind"] == "fresh" and not case["expected"] for case in cases) == 36
    assert sum(case["kind"] == "regression" for case in cases) == 4
    assert all(case["expected"] is False for case in cases if case["kind"] == "regression")
    assert len({case["id"] for case in cases}) == 64
    hard = {case["command"] for case in cases if case.get("hard")}
    assert hard == {"Push the bunk under the window.", "Park the truck under the tree."}


def test_v2_commands_are_preregistered_and_not_v1():
    prereg = PREREG.read_text(encoding="utf-8")
    v1 = V1_CASES.read_text(encoding="utf-8")

    assert all(case["command"] in prereg for case in _v2_cases())
    assert all(case["command"] not in v1 for case in _v2_cases() if case["kind"] == "fresh")


def test_v2_lock_and_modified_case_check(monkeypatch, tmp_path, capsys):
    cases_path = tmp_path / "cases.jsonl"
    lock_path = tmp_path / "cases.lock.json"
    data = probe._cases_bytes(_v2_cases())
    cases_path.write_bytes(data)
    lock_path.write_text(json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "count": 64}), encoding="utf-8")
    monkeypatch.setattr(probe, "V2_CASES_PATH", cases_path)
    monkeypatch.setattr(probe, "V2_LOCK_PATH", lock_path)

    assert probe.main(["--check-corpus", "--corpus", "v2"]) == 0
    cases_path.write_text(
        cases_path.read_text(encoding="utf-8").replace("Feel under the cabinet.", "Feel beside the cabinet."),
        encoding="utf-8",
    )
    assert probe.main(["--check-corpus", "--corpus", "v2"]) == 1
    assert "lock" in capsys.readouterr().out


def test_v2_dry_run_is_128_and_does_not_construct_client(monkeypatch, capsys):
    calls = []

    class NoCallClient:
        @classmethod
        def from_environment(cls):
            calls.append("constructed")
            return cls()

    monkeypatch.setattr(probe, "JevClient", NoCallClient)
    assert probe.main(["--dry-run", "--corpus", "v2"]) == 0
    assert "planned requests: 128" in capsys.readouterr().out
    assert calls == []


class FakeClient:
    last_model = "fake-model"
    last_status = 200

    def __init__(self):
        self.calls = []

    def ask(self, state, questions):
        self.calls.append((state, questions))
        return {"searches_underneath": {"noul": 0.9}}


def test_v2_run_honours_default_cap_and_writes_stop_reason(tmp_path):
    client = FakeClient()
    document = probe.run_cases(_v2_cases(), samples=2, max_calls=128, out=tmp_path / "rows.json", client=client)

    assert len(document["rows"]) == 128
    assert document["stop_reason"] == "max_calls"
    assert len(client.calls) == 128


def test_v2_report_passes_and_counts_nulls(tmp_path):
    rows = _rows_for_v2()
    rows[0]["returned"] = None
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")

    assert probe.report_rows(rows_path, report_path, corpus="v2") == 0
    report = report_path.read_text(encoding="utf-8")
    assert "J1: PASS" in report
    assert "J2: PASS" in report
    assert "R: PASS" in report
    assert "null answers: 1" in report
    assert "probe gate: PASS" in report
    assert "score 0.1" in report


def test_v2_report_fails_each_gate_and_lists_scores(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"

    rows = _rows_for_v2()
    next(row for row in rows if row["case_id"] == "v-n01")["returned"] = True
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path, corpus="v2") == 1
    assert "J1: FAIL" in report_path.read_text(encoding="utf-8")

    rows = _rows_for_v2()
    positive_rows = [row for row in rows if row["case_id"].startswith("v-p")]
    for row in positive_rows[:5]:
        row["returned"] = False
        row["score"] = 0.2
        row["noul"] = 0.2
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path, corpus="v2") == 1
    report = report_path.read_text(encoding="utf-8")
    assert "J2: FAIL" in report
    assert "v-p01" in report and "score 0.2" in report

    rows = _rows_for_v2()
    next(row for row in rows if row["case_id"] == "v-r1")["returned"] = True
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path, corpus="v2") == 1
    assert "R: FAIL" in report_path.read_text(encoding="utf-8")


def test_report_rejects_unknown_corpus(tmp_path):
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps({"rows": []}), encoding="utf-8")

    try:
        probe.report_rows(rows_path, tmp_path / "report.md", corpus="v3")
    except ValueError as error:
        assert str(error) == "unknown corpus: v3"
    else:
        raise AssertionError("unknown corpus was accepted")


def test_v1_files_and_default_check_match_their_lock(capsys):
    lock = json.loads(V1_LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(V1_CASES.read_bytes()).hexdigest() == lock["sha256"]
    assert len(V1_CASES.read_bytes().splitlines()) == lock["count"]
    assert probe.main(["--check-corpus"]) == 0
    assert "corpus literal: PASS" in capsys.readouterr().out


def test_probe2_manifest_generation_matches_committed_json(tmp_path):
    manifest.main(tmp_path)
    generated = json.loads((tmp_path / "run-t9b-probe2-live.json").read_text(encoding="utf-8"))
    committed = json.loads(
        (ROOT / "scripts/ringer/environment_narration/run-t9b-probe2-live.json").read_text(encoding="utf-8")
    )

    assert generated == committed
    task = generated["tasks"][0]
    assert "--corpus v2" in task["spec"]
    assert "--max-calls 128" in task["spec"]
    assert "128" in task["check"]
