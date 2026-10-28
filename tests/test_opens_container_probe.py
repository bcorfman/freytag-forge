import hashlib
import json
from pathlib import Path

from scripts.ringer.environment_narration import make_t9c_probe_run_manifest as manifest
from scripts.ringer.environment_narration import opens_container_probe as probe

PREREG = Path(__file__).parents[1] / ".plans/grounded-llm-environment-narration/t9c-engine-open-prereg.md"


def _questions(case):
    question = case["question"]
    return question if isinstance(question, list) else [question]


def _expected(case, question):
    expected = case["expected"]
    return expected[question] if isinstance(expected, dict) else expected


def _case_groups():
    cases = probe.build_cases()
    return {group: [case for case in cases if case["group"] == group] for group in probe.GROUPS}


def _write_rows(path, rows):
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")


def _correct_rows():
    rows = []
    for case in probe.build_cases():
        for sample in range(2):
            for question in _questions(case):
                answer = _expected(case, question)
                score = 0.9 if answer is True else 0.1
                rows.append(
                    {
                        "case_id": case["id"],
                        "command": case["command"],
                        "thing": case["thing"],
                        "question": question,
                        "sample": sample,
                        "returned": answer,
                        "noul": score,
                        "score": score,
                        "raw_answer": {question: {"noul": score}},
                        "jev_model": "fake-model",
                    }
                )
    return rows


def test_corpus_counts_and_grid_rule():
    groups = _case_groups()
    assert {group: len(cases) for group, cases in groups.items()} == {
        "grid": 60,
        "opening": 20,
        "non-opening": 22,
        "reported": 3,
        "regression": 7,
    }
    assert len({case["id"] for cases in groups.values() for case in cases}) == 112
    assert {case["kind"] for case in groups["regression"]} == {"regression"}
    assert all(case.get("reported") is True for case in groups["reported"])
    assert all(len(_questions(case)) == 2 for case in groups["grid"])

    verbs = ["Inspect", "Examine", "Search", "Check", "Look at"]
    containers = ["cabinet", "chest", "locker", "toolbox"]
    under_words = ["under", "beneath", "underneath", "below"]
    for case in groups["grid"]:
        index = int(case["id"][3:]) - 1
        verb_index = index // 4
        container_index = index % 4
        verb = verbs[verb_index]
        container = containers[container_index]
        under_word = under_words[(verb_index + container_index) % 4]
        if case["kind"] == "bare":
            expected_command = f"{verb} the {container}."
        elif case["kind"] == "under":
            expected_command = (
                f"Look {under_word} the {container}." if verb == "Look at" else f"{verb} {under_word} the {container}."
            )
        else:
            expected_command = (
                f"Look inside the {container}." if verb == "Look at" else f"{verb} inside the {container}."
            )
        assert case["command"] == expected_command
        assert case["thing"] == container


def test_frozen_lists_are_in_prereg_and_do_not_overlap_t9b_lists():
    prereg = PREREG.read_text(encoding="utf-8")
    fresh = [case for case in probe.build_cases() if case["group"] != "grid" and case["group"] != "regression"]
    old_commands = set()
    for relative_path in (
        "scripts/ringer/environment_narration/under_probe/cases.jsonl",
        "scripts/ringer/environment_narration/under_probe_v2/cases.jsonl",
    ):
        for line in Path(relative_path).read_text(encoding="utf-8").splitlines():
            old_commands.add(json.loads(line)["command"])
    assert all(case["command"] in prereg for case in fresh)
    assert all(case["command"] not in old_commands for case in fresh)


def test_lock_matches_and_modified_case_fails_check(monkeypatch, tmp_path, capsys):
    cases_path = tmp_path / "cases.jsonl"
    data = probe._cases_bytes(probe.build_cases())
    cases_path.write_bytes(data)
    lock_path = tmp_path / "cases.lock.json"
    lock_path.write_text(
        json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "count": len(probe.build_cases())}),
        encoding="utf-8",
    )
    monkeypatch.setattr(probe, "CASES_PATH", cases_path)
    monkeypatch.setattr(probe, "LOCK_PATH", lock_path)
    assert probe.main(["--check-corpus"]) == 0
    cases_path.write_text(
        cases_path.read_text(encoding="utf-8").replace("Open the chest.", "Open the box."), encoding="utf-8"
    )
    assert probe.main(["--check-corpus"]) == 1
    assert "lock" in capsys.readouterr().out


def test_dry_run_prints_344_and_makes_no_call(monkeypatch, capsys):
    calls = []

    class NoCallClient:
        @classmethod
        def from_environment(cls):
            calls.append("constructed")
            return cls()

    monkeypatch.setattr(probe, "JevClient", NoCallClient)
    assert probe.main(["--dry-run"]) == 0
    assert "344" in capsys.readouterr().out
    assert calls == []


class FakeClient:
    last_model = "fake-model"
    last_status = 200

    def __init__(self):
        self.calls = []

    def ask(self, state, questions):
        self.calls.append((state, questions))
        question = next(iter(questions))
        return {question: {"noul": 0.9}}


def test_stubbed_run_writes_all_rows_and_records_call_cap(tmp_path):
    client = FakeClient()
    output = tmp_path / "rows.json"
    document = probe.run_cases(probe.build_cases(), samples=2, max_calls=344, out=output, client=client)
    assert len(document["rows"]) == 344
    assert document["stop_reason"] == "max_calls"
    assert len(client.calls) == 344
    assert len([row for row in document["rows"] if row["case_id"].startswith("g-")]) == 240
    assert all("raw_answer" in row and "score" in row for row in document["rows"])
    assert json.loads(output.read_text(encoding="utf-8")) == document


def test_report_gates_each_fail_independently_and_counts_nulls(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows = _correct_rows()
    _write_rows(rows_path, rows)
    assert probe.report_rows(rows_path, report_path) == 0
    report = report_path.read_text(encoding="utf-8")
    assert "probe gate: PASS" in report
    assert "0.9" in report

    mutations = (
        ("J1", lambda row: row["case_id"] == "g-b01" and row["question"] == "opens_container", True),
        (
            "J1b",
            lambda row: (
                row["case_id"] in {"g-i01", "g-i02", "g-i03", "g-i04", "g-i05"} and row["question"] == "opens_container"
            ),
            False,
        ),
        (
            "J2",
            lambda row: (
                row["case_id"] in {"g-b01", "g-b02", "g-b03", "g-b04", "g-b05"}
                and row["question"] == "searches_underneath"
            ),
            True,
        ),
        ("J3", lambda row: row["case_id"] in {"o01", "o02", "o03", "o04", "o05"}, False),
        ("J4", lambda row: row["case_id"] == "n01", True),
        ("R", lambda row: row["case_id"] == "r4", True),
    )
    for gate, matches, value in mutations:
        mutated = [dict(row) for row in rows]
        for row in mutated:
            if matches(row):
                row["returned"] = value
                row["score"] = 0.9 if value else 0.1
                row["noul"] = row["score"]
        _write_rows(rows_path, mutated)
        assert probe.report_rows(rows_path, report_path) == 1
        assert f"{gate}: FAIL" in report_path.read_text(encoding="utf-8")

    null_rows = [dict(row) for row in rows]
    null_rows[0]["returned"] = None
    null_rows[0]["score"] = None
    null_rows[0]["noul"] = None
    _write_rows(rows_path, null_rows)
    assert probe.report_rows(rows_path, report_path) == 0
    assert "null answers: 7" in report_path.read_text(encoding="utf-8")


def test_manifest_is_generated_and_contains_probe_guards(tmp_path):
    manifest.main(tmp_path)
    generated = json.loads((tmp_path / "run-t9c-probe-live.json").read_text(encoding="utf-8"))
    committed = json.loads(
        (Path(__file__).parents[1] / "scripts/ringer/environment_narration/run-t9c-probe-live.json").read_text(
            encoding="utf-8"
        )
    )
    assert generated == committed
    task = generated["tasks"][0]
    assert "--max-calls 344" in task["spec"]
    assert "--max-usd 0.01" in task["spec"]
    assert "344" in task["check"]
    assert "probe gate" in task["check"]
