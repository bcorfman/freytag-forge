import hashlib
import json

import pytest

from scripts.ringer.environment_narration import drain_question_probe as probe
from storygame.runtime.observation_verifier import Relation, _question_for


def _rows(*, missing_narration="Kristin looks around the park.", attempts=None):
    if attempts is None:
        attempts = [{"narration": "real attempt one"}, {"narration": "real attempt two"}]
    return [
        {
            "turns": [
                {
                    "input": "inspect the storm drain",
                    "narration": None,
                    "enforce_attempts": attempts,
                },
                {
                    "input": "inspect the park bench",
                    "narration": missing_narration,
                    "enforce_attempts": [],
                },
            ]
        }
    ]


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


def _case(case_id="d-real-1", kind="positive", label="accept"):
    return {
        "id": case_id,
        "kind": kind,
        "label": label,
        "narration": "Kristin sees the storm drain.",
        "relation": {"thing": "storm drain", "place": "Los Angeles park", "holder": None},
        "source": "test",
    }


def _six_cases():
    return [
        _case("d-real-1"),
        _case("d-real-2"),
        _case("d-explicit"),
        _case("d-missing", "negative", "reject"),
        _case("d-remembered", "negative", "reject"),
        _case("d-elsewhere", "negative", "reject"),
    ]


def test_build_cases_uses_recorded_attempts_and_rejects_bad_corpus(tmp_path):
    rows_path = tmp_path / "rows.json"
    _write_rows(rows_path, _rows())

    cases = probe.build_cases(rows_path)

    assert [case["id"] for case in cases] == [
        "d-real-1",
        "d-real-2",
        "d-missing",
        "d-explicit",
        "d-remembered",
        "d-elsewhere",
    ]
    assert cases[0]["narration"] == "real attempt one"
    assert cases[1]["narration"] == "real attempt two"
    assert cases[2]["kind"] == "negative"
    assert cases[2]["label"] == "reject"
    assert cases[2]["relation"] == {
        "thing": "storm drain",
        "place": "Los Angeles park",
        "holder": None,
    }
    assert all(set(case) == {"id", "kind", "label", "narration", "relation", "source"} for case in cases)

    _write_rows(rows_path, _rows(missing_narration="Kristin notices the drain near the bench."))
    with pytest.raises(ValueError) as error:
        probe.build_cases(rows_path)
    assert "d-missing" in str(error.value)

    _write_rows(rows_path, _rows(attempts=[{"narration": "only one"}]))
    with pytest.raises(ValueError) as error:
        probe.build_cases(rows_path)
    assert "exactly two" in str(error.value)


def test_committed_cases_have_six_ids_and_matching_lock():
    cases = probe._load_cases()

    assert [case["id"] for case in cases] == [
        "d-real-1",
        "d-real-2",
        "d-missing",
        "d-explicit",
        "d-remembered",
        "d-elsewhere",
    ]
    assert probe._lock_matches(cases)


def test_request_payloads_preserve_product_question_and_state(monkeypatch):
    case = _case()
    relation = Relation(**case["relation"])
    product_question = _question_for(relation)

    j0 = probe._request_payload(case, "J0")
    j1 = probe._request_payload(case, "J1")
    j2 = probe._request_payload(case, "J2")

    assert j0["input"] == {"state": {"narration": case["narration"]}, "questions": {"relation_0": product_question}}
    assert j1["input"]["questions"] == {"relation_0": product_question}
    assert j1["input"]["state"] == {
        "narration": case["narration"],
        "scene": "The Lead in the Park",
        "starting_place": "Los Angeles park",
    }
    assert j2["input"]["state"] == j1["input"]["state"]
    assert j2["input"]["questions"]["relation_0"]["criteria"] == product_question["criteria"]
    assert j2["input"]["questions"]["relation_0"]["type"] == product_question["type"]
    assert j2["input"]["questions"]["relation_0"]["instructions"] != product_question["instructions"]
    assert (
        j2["input"]["questions"]["relation_0"]["instructions"].count(
            "Check whether the narration shows the named thing in the scene."
        )
        == 1
    )

    def missing_sentence(relation):
        return {"type": "noul", "instructions": "product wording changed", "criteria": {}}

    monkeypatch.setattr(probe, "_question_for", missing_sentence)
    with pytest.raises(ValueError) as error:
        probe.question_for_arm(relation, "J2")
    assert "J2" in str(error.value)


def test_planned_calls_are_180_and_seeded_order_is_deterministic():
    cases = _six_cases()

    first = probe._planned_calls(cases, 10)
    second = probe._planned_calls(cases, 10)

    assert len(first) == 180
    assert first == second
    assert [arm for _, arm, _ in first[:3]] == ["J0", "J1", "J2"]
    assert [sample for _, _, sample in first[:3]] == [0, 0, 0]


@pytest.mark.parametrize(
    "arguments, expected",
    [
        (["--run"], "requires --confirm"),
        (["--run", "--confirm", "--max-calls", "179"], "exceed --max-calls"),
        (["--run", "--confirm", "--max-calls", "180", "--max-usd", "0"], "exceeds --max-usd"),
    ],
)
def test_run_refusals(monkeypatch, tmp_path, capsys, arguments, expected):
    cases = _six_cases()
    _write_cases_and_lock(monkeypatch, tmp_path, cases)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)

    assert probe.main(arguments + ["--out", str(tmp_path / "rows.json")]) == 2
    assert expected in capsys.readouterr().err


def test_run_refuses_bad_lock(monkeypatch, tmp_path, capsys):
    cases = _six_cases()
    _write_cases_and_lock(monkeypatch, tmp_path, cases)
    monkeypatch.setattr(probe, "LOCK_PATH", tmp_path / "bad.lock.json")
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "redacted-test-token")

    assert probe.main(["--run", "--confirm", "--out", str(tmp_path / "rows.json")]) == 2
    assert "matching lock" in capsys.readouterr().err


class FakeClient:
    last_model = "fake-model"
    last_status = 200

    def __init__(self, answer=None):
        self.answer = answer or {"relation_0": {"noul": 0.9}}
        self.calls = []

    def ask(self, state, questions):
        self.calls.append((state, questions))
        return self.answer


class UnusableClient(FakeClient):
    def ask(self, state, questions):
        self.calls.append((state, questions))
        return None


def test_run_writes_180_rows_and_stops_after_three_unusable_replies(tmp_path):
    cases = _six_cases()
    output = tmp_path / "run.json"
    client = FakeClient()

    document = probe.run_cases(cases, samples=10, max_calls=180, out=output, client=client)

    assert len(document["rows"]) == 180
    assert len(client.calls) == 180
    assert output.exists()
    assert all(row["outcome"] == "ok" for row in document["rows"])

    stopped = probe.run_cases(cases, samples=10, max_calls=180, out=tmp_path / "stopped.json", client=UnusableClient())
    assert len(stopped["rows"]) == 3
    assert stopped["stop_reason"] == "three_consecutive_unusable"


def _report_rows():
    rows = []
    for arm in probe.QUESTION_ARMS:
        for kind, case_ids in (
            ("positive", ("d-real-1", "d-real-2", "d-explicit")),
            ("negative", ("d-missing", "d-remembered", "d-elsewhere")),
        ):
            for case_id in case_ids:
                for sample in range(10):
                    accepts = kind == "positive" and sample < 9
                    verdict = "accept" if accepts else "reject"
                    rows.append(
                        {
                            "case_id": case_id,
                            "kind": kind,
                            "label": "accept" if kind == "positive" else "reject",
                            "arm": arm,
                            "sample": sample,
                            "verdict": verdict,
                            "score": 0.9 if accepts else 0.1,
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
    assert "J0" in report and "J1" in report and "J2" in report
    assert "positive accepts/uncertain/rejects: 27/0/3 of 30" in report
    assert "J1 vs J0 G1: PASS" in report and "J2 vs J0 G1: PASS" in report
    assert "J1 vs J0 G2: PASS" in report and "J2 vs J0 G2: PASS" in report
    assert "J1 vs J0 G3: PASS" in report and "J2 vs J0 G3: PASS" in report
    assert "score range" in report

    rows = _report_rows()
    for row in rows:
        if row["arm"] in {"J1", "J2"} and row["kind"] == "negative" and row["sample"] == 9:
            row["verdict"] = "accept"
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path) == 1
    report = report_path.read_text(encoding="utf-8")
    assert "J1 vs J0 G1: FAIL" in report
    assert "J2 vs J0 G1: FAIL" in report


def test_no_credential_value_in_output(monkeypatch, capsys):
    secret = "super-secret-drain-probe-token"
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", secret)

    assert probe.main(["--dry-run", "--samples", "1"]) == 0
    assert secret not in capsys.readouterr().out
