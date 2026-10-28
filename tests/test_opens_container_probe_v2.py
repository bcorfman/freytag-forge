import hashlib
import json
from pathlib import Path

from scripts.ringer.environment_narration import make_t9d_probe_run_manifest as manifest
from scripts.ringer.environment_narration import opens_container_probe as probe

ROOT = Path(__file__).parents[1]
PREREG = ROOT / ".plans/grounded-llm-environment-narration/t9d-search-opens-prereg.md"


def _questions(case):
    question = case["question"]
    return question if isinstance(question, list) else [question]


def _expected(case, question):
    expected = case["expected"]
    return expected[question] if isinstance(expected, dict) else expected


def _groups():
    cases = probe.build_cases("v2")
    return {group: [case for case in cases if case["group"] == group] for group in {case["group"] for case in cases}}


def _rows(returned_by_case=None):
    returned_by_case = returned_by_case or {}
    rows = []
    for case in probe.build_cases("v2"):
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


def test_v2_corpus_counts_questions_and_request_count():
    groups = _groups()
    assert {group: len(cases) for group, cases in groups.items()} == {
        "grid": 60,
        "search-positive": 16,
        "look-negative": 16,
        "opening": 20,
        "non-opening": 22,
        "reported": 3,
        "regression": 12,
    }
    cases = probe.build_cases("v2")
    assert len({case["id"] for case in cases}) == len(cases)
    assert sum(len(_questions(case)) for case in cases) * 2 == 378
    assert sum(len(_questions(case)) for case in cases) == 189


def test_v2_grid_is_generated_from_preregistered_rule():
    groups = _groups()
    grid = groups["grid"]
    verbs = ["Search", "Inspect", "Examine", "Check", "Look at"]
    containers = ["dresser", "trunk", "suitcase", "cupboard"]
    under_words = ["under", "beneath", "underneath", "below"]
    assert len([case for case in grid if case["kind"] == "bare"]) == 20
    assert len([case for case in grid if case["kind"] == "under"]) == 20
    assert len([case for case in grid if case["kind"] == "inside"]) == 20
    for case in grid:
        index = int(case["id"][3:]) - 1
        verb_index, container_index = divmod(index, 4)
        verb = verbs[verb_index]
        container = containers[container_index]
        under_word = under_words[(verb_index + container_index) % 4]
        if case["kind"] == "bare":
            expected_command = f"{verb} the {container}."
            expected_questions = ["opens_container", "searches_underneath"]
            expected = {"opens_container": verb == "Search", "searches_underneath": False}
        elif case["kind"] == "under":
            expected_command = (
                f"Look under the {container}." if verb == "Look at" else f"{verb} {under_word} the {container}."
            )
            expected_questions = ["searches_underneath"]
            expected = {"searches_underneath": True}
        else:
            expected_command = (
                f"Look inside the {container}." if verb == "Look at" else f"{verb} inside the {container}."
            )
            expected_questions = ["opens_container", "searches_underneath"]
            expected = {"opens_container": True, "searches_underneath": False}
        assert case["command"] == expected_command
        assert case["thing"] == container
        assert _questions(case) == expected_questions
        assert case["expected"] == expected


def test_all_v2_commands_are_in_prereg_and_fresh_lists_do_not_overlap_old_probes():
    prereg = PREREG.read_text(encoding="utf-8")
    cases = probe.build_cases("v2")
    assert all(case["command"] in prereg for case in cases if case["group"] != "grid")
    old_commands = set()
    for relative_path in (
        "scripts/ringer/environment_narration/opens_probe/cases.jsonl",
        "scripts/ringer/environment_narration/under_probe/cases.jsonl",
        "scripts/ringer/environment_narration/under_probe_v2/cases.jsonl",
    ):
        for line in (ROOT / relative_path).read_text(encoding="utf-8").splitlines():
            old_commands.add(json.loads(line)["command"])
    fresh_groups = {"grid", "search-positive", "look-negative"}
    fresh_commands = [case["command"] for case in cases if case["group"] in fresh_groups]
    overlaps = {command for command in fresh_commands if command in old_commands}
    assert overlaps == {"Search the toolbox.", "Inspect the toolbox.", "Search the cooler."}
    assert all(
        case["command"] not in old_commands
        for case in cases
        if case["group"] == "grid" and case["thing"] not in {"toolbox", "cooler"}
    )


def test_v2_lock_matches_and_modified_case_fails_check(monkeypatch, tmp_path, capsys):
    cases_path = tmp_path / "cases.jsonl"
    data = probe._cases_bytes(probe.build_cases("v2"))
    cases_path.write_bytes(data)
    lock_path = tmp_path / "cases.lock.json"
    lock_path.write_text(
        json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "count": len(probe.build_cases("v2"))}),
        encoding="utf-8",
    )
    monkeypatch.setattr(probe, "V2_CASES_PATH", cases_path)
    monkeypatch.setattr(probe, "V2_LOCK_PATH", lock_path)
    assert probe.main(["--corpus", "v2", "--check-corpus"]) == 0
    cases_path.write_text(
        cases_path.read_text(encoding="utf-8").replace("Search the dresser.", "Search the box."),
        encoding="utf-8",
    )
    assert probe.main(["--corpus", "v2", "--check-corpus"]) == 1
    assert "lock" in capsys.readouterr().out


def test_v2_dry_run_prints_378_without_constructing_client(monkeypatch, capsys):
    calls = []

    class NoCallClient:
        @classmethod
        def from_environment(cls):
            calls.append("constructed")
            return cls()

    monkeypatch.setattr(probe, "JevClient", NoCallClient)
    assert probe.main(["--corpus", "v2", "--dry-run"]) == 0
    assert "planned requests: 378" in capsys.readouterr().out
    assert calls == []


class FakeClient:
    last_model = "fake-model"
    last_status = 200

    def __init__(self):
        self.calls = []

    def ask(self, state, questions):
        self.calls.append((state, questions))
        answer = {question: {"noul": 0.9} for question in questions}
        return answer


def test_v2_stubbed_run_writes_378_rows_and_raw_scores(tmp_path):
    client = FakeClient()
    output = tmp_path / "rows.json"
    document = probe.run_cases(probe.build_cases("v2"), samples=2, max_calls=378, out=output, client=client)
    assert len(document["rows"]) == 378
    assert document["stop_reason"] == "max_calls"
    assert len(client.calls) == 378
    assert all("raw_answer" in row and "score" in row for row in document["rows"])
    assert json.loads(output.read_text(encoding="utf-8")) == document


def test_v2_report_passes_when_all_answers_match_and_counts_none(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows = _rows()
    _write_rows(rows_path, rows)
    assert probe.report_rows(rows_path, report_path, corpus="v2") == 0
    report = report_path.read_text(encoding="utf-8")
    assert "probe gate: PASS" in report
    assert all(f"K{number}: PASS" in report for number in range(1, 7))

    rows[0]["returned"] = None
    rows[0]["score"] = None
    rows[0]["noul"] = None
    _write_rows(rows_path, rows)
    assert probe.report_rows(rows_path, report_path, corpus="v2") == 0
    assert "null answers: 7" in report_path.read_text(encoding="utf-8")


def test_each_v2_gate_fails_independently_and_names_a_miss(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    mutations = (
        ("K1", [("g-b01", "opens_container")], False),
        ("K2", [("g-b05", "opens_container")], True),
        ("K3", [("g-i01", "opens_container"), ("g-i02", "opens_container"), ("g-i03", "opens_container")], False),
        (
            "K4",
            [("g-u01", "searches_underneath"), ("g-u02", "searches_underneath")],
            False,
        ),
        ("K5", [("o01", "opens_container"), ("o02", "opens_container"), ("o03", "opens_container")], False),
        ("K6", [("r01", "opens_container")], False),
    )
    for gate, keys, value in mutations:
        rows = _rows({key: value for key in keys})
        _write_rows(rows_path, rows)
        assert probe.report_rows(rows_path, report_path, corpus="v2") == 1
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
    assert probe.main(["--corpus", "v2", "--run", "--out", str(tmp_path / "rows.json")]) != 0
    assert calls == []


def test_t9d_manifest_regeneration_is_byte_for_byte(tmp_path):
    manifest.main(tmp_path)
    generated = (tmp_path / "run-t9d-probe-live.json").read_bytes()
    committed = (ROOT / "scripts/ringer/environment_narration/run-t9d-probe-live.json").read_bytes()
    assert generated == committed
