import hashlib
import json
from pathlib import Path

from scripts.ringer.environment_narration import under_question_probe as probe

ROOT = Path(__file__).parents[1]
PREREG = ROOT / ".plans/grounded-llm-environment-narration/t9h-confirmation-prereg.md"
V1_CASES = ROOT / "scripts/ringer/environment_narration/under_probe/cases.jsonl"
V2_CASES = ROOT / "scripts/ringer/environment_narration/under_probe_v2/cases.jsonl"

US_COMMANDS = [
    "Look under the workstation.",
    "Search under the park bench.",
    "Check beneath the executive desk.",
    "Feel under the sofa.",
    "Look under the coffee table.",
    "Inspect underneath the bed.",
    "Look beneath the bookshelf.",
    "Search under the chair.",
    "Check under the stool.",
    "Feel beneath the counter.",
    "Look under the picnic table.",
    "Examine below the bench.",
]
UB_COMMANDS = [
    "Inspect the workstation.",
    "Search the park bench.",
    "Examine the executive desk.",
    "Check the sofa.",
    "Look at the coffee table.",
    "Inspect the bed.",
    "Search the bookshelf.",
    "Examine the chair.",
    "Check the stool.",
    "Look at the counter.",
    "Search the picnic table.",
    "Inspect the bench.",
]


def _v4_cases():
    return probe._load_cases(corpus="v4")


def _rows_for_v4():
    rows = []
    for case in _v4_cases():
        for sample in range(2):
            returned = case["expected"]
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


def test_v4_corpus_literal_has_exact_commands_labels_and_question():
    cases = _v4_cases()

    assert len(cases) == 24
    assert [case["command"] for case in cases] == US_COMMANDS + UB_COMMANDS
    assert [case["label"] for case in cases] == ["US"] * 12 + ["UB"] * 12
    assert [case["expected"] for case in cases] == [True] * 12 + [False] * 12
    assert all(case["question"] == "searches_underneath" for case in cases)
    assert len({case["id"] for case in cases}) == 24


def test_v4_commands_are_preregistered_and_not_in_v1_or_v2():
    prereg = PREREG.read_text(encoding="utf-8")
    v1 = V1_CASES.read_text(encoding="utf-8")
    v2 = V2_CASES.read_text(encoding="utf-8")

    assert all(case["command"] in prereg for case in _v4_cases())
    assert all(case["command"] not in v1 for case in _v4_cases())
    assert all(case["command"] not in v2 for case in _v4_cases())


def test_v4_lock_and_check_corpus(monkeypatch, tmp_path, capsys):
    cases_path = tmp_path / "cases.jsonl"
    lock_path = tmp_path / "cases.lock.json"
    data = probe._cases_bytes(_v4_cases())
    cases_path.write_bytes(data)
    lock_path.write_text(json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "count": 24}), encoding="utf-8")
    monkeypatch.setattr(probe, "V4_CASES_PATH", cases_path)
    monkeypatch.setattr(probe, "V4_LOCK_PATH", lock_path)

    assert probe.main(["--check-corpus", "--corpus", "v4"]) == 0
    assert "corpus literal: PASS" in capsys.readouterr().out


def test_v4_dry_run_reports_48_without_constructing_client(monkeypatch, capsys):
    calls = []

    class NoCallClient:
        @classmethod
        def from_environment(cls):
            calls.append("constructed")
            return cls()

    monkeypatch.setattr(probe, "JevClient", NoCallClient)
    assert probe.main(["--dry-run", "--corpus", "v4"]) == 0
    assert "planned requests: 48" in capsys.readouterr().out
    assert calls == []


def test_v4_run_asks_only_searches_underneath(tmp_path):
    class FakeClient:
        last_model = "fake-model"
        last_status = 200

        def __init__(self):
            self.questions = []

        def ask(self, state, questions):
            self.questions.append(questions)
            return {"searches_underneath": {"noul": 0.9}}

    client = FakeClient()
    document = probe.run_cases(_v4_cases(), samples=2, max_calls=48, out=tmp_path / "rows.json", client=client)

    assert len(document["rows"]) == 48
    assert all(question.keys() == {"searches_underneath"} for question in client.questions)


def test_v4_report_passes_and_counts_nulls(tmp_path):
    rows = _rows_for_v4()
    rows[0]["returned"] = None
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")

    assert probe.report_rows(rows_path, report_path, corpus="v4") == 0
    report = report_path.read_text(encoding="utf-8")
    assert "P1: PASS" in report
    assert "P2: PASS" in report
    assert "null answers: 1" in report
    assert "probe gate: PASS" in report
    assert "score 0.9" in report


def test_v4_report_fails_with_three_us_misses(tmp_path):
    rows = _rows_for_v4()
    for row in [row for row in rows if row["case_id"].startswith("us")][:3]:
        row["returned"] = False
        row["score"] = 0.2
        row["noul"] = 0.2
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")

    assert probe.report_rows(rows_path, report_path, corpus="v4") == 1
    report = report_path.read_text(encoding="utf-8")
    assert "P1: FAIL" in report
    assert "us01" in report
    assert "score 0.2" in report
    assert "probe gate: FAIL" in report


def test_v4_report_fails_with_three_ub_true_answers(tmp_path):
    rows = _rows_for_v4()
    for row in [row for row in rows if row["case_id"].startswith("ub")][:3]:
        row["returned"] = True
        row["score"] = 0.8
        row["noul"] = 0.8
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")

    assert probe.report_rows(rows_path, report_path, corpus="v4") == 1
    report = report_path.read_text(encoding="utf-8")
    assert "P1: PASS" in report
    assert "P2: FAIL" in report
    assert "ub01" in report
    assert "probe gate: FAIL" in report


def test_v1_and_v2_caps_remain_unchanged():
    assert probe._corpus_max_calls("v1") == 98
    assert probe._corpus_max_calls("v2") == 128
