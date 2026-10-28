import hashlib
import json
from pathlib import Path

from scripts.ringer.environment_narration import make_t9e_probe_run_manifest as manifest
from scripts.ringer.environment_narration import opens_container_probe as probe

ROOT = Path(__file__).parents[1]
PREREG = ROOT / ".plans/grounded-llm-environment-narration/t9e-check-wording-prereg.md"


def _questions(case):
    question = case["question"]
    return question if isinstance(question, list) else [question]


def _expected(case, question):
    expected = case["expected"]
    return expected[question] if isinstance(expected, dict) else expected


def _groups():
    cases = probe.build_cases("v3")
    return {group: [case for case in cases if case["group"] == group] for group in {case["group"] for case in cases}}


def _rows(returned_by_case=None):
    returned_by_case = returned_by_case or {}
    rows = []
    for case in probe.build_cases("v3"):
        for sample in range(2):
            for question in _questions(case):
                returned = returned_by_case.get((case["id"], question), _expected(case, question))
                score = None if returned is None else (0.9 if returned else 0.1)
                rows.append(
                    {
                        "case_id": case["id"],
                        "command": case["command"],
                        "thing": case["thing"],
                        "question": question,
                        "sample": sample,
                        "returned": returned,
                        "noul": score,
                        "score": score,
                        "raw_answer": {question: {"noul": score}},
                        "jev_model": "fake-model",
                    }
                )
    return rows


def _write_rows(path, rows):
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")


def test_v3_corpus_counts_questions_and_request_count():
    groups = _groups()
    assert {group: len(cases) for group, cases in groups.items()} == {
        "fresh-look": 24,
        "fresh-search": 8,
        "fresh-inside": 8,
        "fresh-under": 8,
        "miss": 1,
        "regression": 12,
        "opening": 20,
        "non-opening": 22,
    }
    cases = probe.build_cases("v3")
    assert len({case["id"] for case in cases}) == len(cases)
    assert sum(len(_questions(case)) for case in cases) == 103
    assert sum(len(_questions(case)) for case in cases) * 2 == 206


def test_v3_fresh_commands_and_miss_are_in_prereg_and_are_new():
    prereg = PREREG.read_text(encoding="utf-8")
    old_commands = set()
    for relative_path in (
        "scripts/ringer/environment_narration/opens_probe/cases.jsonl",
        "scripts/ringer/environment_narration/opens_probe_v2/cases.jsonl",
    ):
        for line in (ROOT / relative_path).read_text(encoding="utf-8").splitlines():
            old_commands.add(json.loads(line)["command"])

    fresh_groups = {"fresh-look", "fresh-search", "fresh-inside", "fresh-under"}
    fresh_cases = [case for case in probe.build_cases("v3") if case["group"] in fresh_groups]
    miss_cases = [case for case in probe.build_cases("v3") if case["group"] == "miss"]
    assert all(case["command"] in prereg for case in fresh_cases + miss_cases)
    assert all(case["command"] not in old_commands for case in fresh_cases)


def test_v3_lock_matches_and_modified_case_fails_check(monkeypatch, tmp_path, capsys):
    cases_path = tmp_path / "cases.jsonl"
    data = probe._cases_bytes(probe.build_cases("v3"))
    cases_path.write_bytes(data)
    lock_path = tmp_path / "cases.lock.json"
    lock_path.write_text(
        json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "count": len(probe.build_cases("v3"))}),
        encoding="utf-8",
    )
    monkeypatch.setattr(probe, "V3_CASES_PATH", cases_path)
    monkeypatch.setattr(probe, "V3_LOCK_PATH", lock_path)
    assert probe.main(["--corpus", "v3", "--check-corpus"]) == 0
    cases_path.write_text(
        cases_path.read_text(encoding="utf-8").replace("Check the mailbox.", "Check the box."),
        encoding="utf-8",
    )
    assert probe.main(["--corpus", "v3", "--check-corpus"]) == 1
    assert "lock" in capsys.readouterr().out


def test_v3_dry_run_prints_206_without_constructing_client(monkeypatch, capsys):
    calls = []

    class NoCallClient:
        @classmethod
        def from_environment(cls):
            calls.append("constructed")
            return cls()

    monkeypatch.setattr(probe, "JevClient", NoCallClient)
    assert probe.main(["--corpus", "v3", "--dry-run"]) == 0
    assert "planned requests: 206" in capsys.readouterr().out
    assert calls == []


class FakeClient:
    last_model = "fake-model"
    last_status = 200

    def __init__(self):
        self.calls = []

    def ask(self, state, questions):
        self.calls.append((state, questions))
        return {question: {"noul": 0.9} for question in questions}


def test_v3_stubbed_run_writes_206_rows_and_raw_scores(tmp_path):
    client = FakeClient()
    output = tmp_path / "rows.json"
    document = probe.run_cases(probe.build_cases("v3"), samples=2, max_calls=206, out=output, client=client)
    assert len(document["rows"]) == 206
    assert document["stop_reason"] == "max_calls"
    assert len(client.calls) == 206
    assert all("raw_answer" in row and "score" in row for row in document["rows"])
    assert json.loads(output.read_text(encoding="utf-8")) == document


def test_v3_report_passes_when_all_answers_match_and_counts_none(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows = _rows()
    rows[0]["returned"] = None
    rows[0]["score"] = None
    rows[0]["noul"] = None
    _write_rows(rows_path, rows)
    assert probe.report_rows(rows_path, report_path, corpus="v3") == 0
    report = report_path.read_text(encoding="utf-8")
    assert "probe gate: PASS" in report
    assert "null answers: 1" in report
    assert all(f"M{number}: PASS" in report for number in range(1, 4))


def test_each_v3_gate_fails_independently_and_names_a_miss(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    mutations = (
        ("M1", [("fl01", "opens_container")], True),
        ("M1", [("m01", "opens_container")], True),
        ("M2", [("fs01", "opens_container"), ("fs02", "opens_container"), ("fs03", "opens_container")], False),
        ("M3", [("r01", "opens_container")], False),
    )
    for gate, keys, value in mutations:
        rows = _rows({key: value for key in keys})
        _write_rows(rows_path, rows)
        assert probe.report_rows(rows_path, report_path, corpus="v3") == 1
        report = report_path.read_text(encoding="utf-8")
        assert f"{gate}: FAIL" in report
        assert all(case_id in report for case_id, _ in keys)


def test_run_without_confirm_exits_without_constructing_or_calling_client(monkeypatch, tmp_path):
    calls = []

    class NoCallClient:
        @classmethod
        def from_environment(cls):
            calls.append("constructed")
            return cls()

    monkeypatch.setattr(probe, "JevClient", NoCallClient)
    assert probe.main(["--corpus", "v3", "--run", "--out", str(tmp_path / "rows.json")]) != 0
    assert calls == []


def test_t9e_manifest_regeneration_is_byte_for_byte(tmp_path):
    manifest.main(tmp_path)
    generated = (tmp_path / "run-t9e-probe-live.json").read_bytes()
    committed = (ROOT / "scripts/ringer/environment_narration/run-t9e-probe-live.json").read_bytes()
    assert generated == committed
