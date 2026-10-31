import json

import pytest

from scripts.ringer.environment_narration import j1_screen_probe as probe
from storygame.runtime.observation_verifier import Relation, _question_for


def _corpus_case(case_id="c1", relations=None):
    if relations is None:
        relations = [{"thing": "lantern", "place": "the quay", "holder": None, "label": "accept"}]
    return {
        "id": case_id,
        "story": "quay",
        "category": "positive_plain",
        "narration": "Mara sees the lantern.",
        "relations": relations,
        "undetectable_invention": False,
        "note": "test",
    }


def _heldout_case(case_id="h1", label="accept", negative_type=None):
    return {
        "id": case_id,
        "story": "The Quay Story",
        "scene": "The Quay",
        "kind": "positive" if label == "accept" else "negative",
        "note": "test",
        "narration": "Mara sees the lantern.",
        "relation": {"thing": "lantern", "place": "The Quay", "holder": None},
        "label": label,
        "negative_type": negative_type,
    }


def _corpus_document(cases):
    return {
        "cases": cases,
        "combined": "corpus-hash",
        "file_hashes": {},
        "file_lines": {},
        "category_counts": {},
        "story_counts": {},
        "label_counts": {},
        "relation_count": sum(len(case["relations"]) for case in cases),
    }


def _install_fixture(monkeypatch, tmp_path, cases=None, heldout=None):
    cases = [_corpus_case()] if cases is None else cases
    heldout = [_heldout_case()] if heldout is None else heldout
    corpus = _corpus_document(cases)
    heldout_path = tmp_path / "heldout.jsonl"
    heldout_path.write_text("".join(json.dumps(case) + "\n" for case in heldout), encoding="utf-8")
    monkeypatch.setattr(probe, "HELDOUT_PATH", heldout_path)
    monkeypatch.setattr(probe, "_validated_corpus", lambda: corpus)
    monkeypatch.setattr(probe, "_corpus_lock_matches", lambda value: True)
    return cases, heldout, corpus


def test_request_payloads_keep_questions_and_only_add_j1m_state():
    relation = Relation(thing="lantern", place="the quay", holder=None)
    corpus = _corpus_case(relations=[{**relation.__dict__, "label": "accept"}])
    heldout = _heldout_case()

    corpus_v0 = probe._request_payload(corpus, "V0", "corpus")
    corpus_j1m = probe._request_payload(corpus, "J1m", "corpus")
    heldout_v0 = probe._request_payload(heldout, "V0", "heldout")
    heldout_j1m = probe._request_payload(heldout, "J1m", "heldout")

    assert corpus_v0["input"]["questions"] == corpus_j1m["input"]["questions"]
    assert heldout_v0["input"]["questions"] == heldout_j1m["input"]["questions"]
    assert corpus_v0["input"]["state"] == {"narration": corpus["narration"]}
    assert corpus_j1m["input"]["state"] == {
        "narration": corpus["narration"],
        "scene": corpus["story"],
        "starting_places": {"lantern": "the quay"},
    }
    assert heldout_j1m["input"]["state"]["scene"] == heldout["scene"]
    assert heldout_j1m["input"]["state"]["starting_places"] == {"lantern": "The Quay"}
    assert corpus_j1m["input"]["questions"]["relation_0"] == _question_for(relation)

    with_holder = _corpus_case(relations=[{"thing": "lantern", "place": None, "holder": "Mara", "label": "accept"}])
    assert probe._request_payload(with_holder, "J1m", "corpus")["input"]["state"]["starting_places"] == {}


def test_validate_good_and_bad_heldout_fixture(monkeypatch, tmp_path, capsys):
    _install_fixture(monkeypatch, tmp_path)
    assert probe.main(["--validate"]) == 0
    assert "corpus case count: 1" in capsys.readouterr().out

    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"id": "bad"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(probe, "HELDOUT_PATH", bad)
    assert probe.main(["--validate"]) == 1
    assert "held-out validation failed" in capsys.readouterr().err


def test_lock_then_run_refuses_changed_heldout(monkeypatch, tmp_path, capsys):
    _install_fixture(monkeypatch, tmp_path)
    lock_path = tmp_path / "lock.json"
    monkeypatch.setattr(probe, "LOCK_PATH", lock_path)
    assert probe.main(["--lock"]) == 0

    heldout_path = probe.HELDOUT_PATH
    heldout_path.write_text(
        json.dumps({**_heldout_case(), "narration": "Mara does not see the lantern."}) + "\n", encoding="utf-8"
    )

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--samples-corpus",
                "1",
                "--samples-heldout",
                "1",
                "--out",
                str(tmp_path / "rows.json"),
            ]
        )
        == 2
    )
    assert "matching lock" in capsys.readouterr().err


def test_planned_calls_default_arithmetic_and_seeded_order():
    assert probe._planned_count(224, 40, 2, 5) == 1296
    cases = [_corpus_case("a"), _corpus_case("b")]
    heldout = [_heldout_case("x")]
    first = probe._planned_calls(cases, heldout, samples_corpus=2, samples_heldout=3)
    second = probe._planned_calls(cases, heldout, samples_corpus=2, samples_heldout=3)
    assert first == second
    assert len(first) == 14
    assert [(item["set"], item["arm"], item["sample"]) for item in first[:4]] == [
        ("corpus", "V0", 0),
        ("corpus", "J1m", 0),
        ("corpus", "V0", 0),
        ("corpus", "J1m", 0),
    ]


@pytest.mark.parametrize(
    "arguments, expected",
    [
        (["--run"], "requires --confirm"),
        (["--run", "--confirm", "--max-calls", "3"], "exceed --max-calls"),
        (["--run", "--confirm", "--max-usd", "0"], "exceeds --max-usd"),
    ],
)
def test_run_refusals(monkeypatch, tmp_path, capsys, arguments, expected):
    _install_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(probe, "_ceiling", lambda *args: 0.01)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")
    assert (
        probe.main(
            arguments
            + [
                "--samples-corpus",
                "1",
                "--samples-heldout",
                "1",
                "--out",
                str(tmp_path / "rows.json"),
            ]
        )
        == 2
    )
    assert expected in capsys.readouterr().err


class FakeClient:
    last_model = "fake-model"
    last_version = "fake-version"
    last_status = 200

    def __init__(self, answer=None, raise_after=None):
        self.answer = answer or {"relation_0": {"noul": 0.9}}
        self.raise_after = raise_after
        self.calls = []

    def ask(self, state, questions):
        if self.raise_after is not None and len(self.calls) >= self.raise_after:
            raise RuntimeError("fake failure")
        self.calls.append((state, questions))
        return self.answer


def test_fake_client_run_writes_all_rows_and_final_null_stop_reason(tmp_path):
    cases = [_corpus_case()]
    heldout = [_heldout_case()]
    output = tmp_path / "rows.json"
    client = FakeClient()
    document = probe.run_cases(
        cases,
        heldout,
        samples_corpus=1,
        samples_heldout=1,
        max_calls=4,
        out=output,
        client=client,
        corpus_hash="corpus-hash",
        heldout_hash="heldout-hash",
    )
    assert len(document["rows"]) == 4
    assert len(client.calls) == 4
    assert json.loads(output.read_text(encoding="utf-8"))["stop_reason"] is None
    assert {row["arm"] for row in document["rows"]} == {"V0", "J1m"}
    assert {row["set"] for row in document["rows"]} == {"corpus", "heldout"}


def test_fake_client_exception_leaves_incomplete_document(tmp_path):
    output = tmp_path / "rows.json"
    with pytest.raises(RuntimeError) as error:
        probe.run_cases(
            [_corpus_case()],
            [_heldout_case()],
            samples_corpus=1,
            samples_heldout=1,
            max_calls=4,
            out=output,
            client=FakeClient(raise_after=2),
            corpus_hash="corpus-hash",
            heldout_hash="heldout-hash",
        )
    assert str(error.value) == "fake failure"
    document = json.loads(output.read_text(encoding="utf-8"))
    assert len(document["rows"]) == 2
    assert document["stop_reason"] == "incomplete"


def test_run_stops_after_three_unusable_replies(tmp_path):
    class UnusableClient(FakeClient):
        def ask(self, state, questions):
            self.calls.append((state, questions))
            return None

    output = tmp_path / "rows.json"
    document = probe.run_cases(
        [_corpus_case(), _corpus_case("c2")],
        [],
        samples_corpus=2,
        samples_heldout=1,
        max_calls=4,
        out=output,
        client=UnusableClient(),
        corpus_hash="corpus-hash",
        heldout_hash="heldout-hash",
    )
    assert len(document["rows"]) == 3
    assert document["stop_reason"] == "three_consecutive_unusable"


def _row(set_name, arm, case_id, verdict, label, category="positive_plain", negative_type=None, sample=0):
    return {
        "set": set_name,
        "arm": arm,
        "case_id": case_id,
        "sample": sample,
        "story": "quay",
        "category": category,
        "negative_type": negative_type,
        "relations": [{"thing": "lantern", "label": label, "verdict": verdict, "score": 0.9}],
        "latency_ms": 10,
        "jev_model": "fake-model",
        "jev_version": "fake-version",
    }


def _gate_rows():
    rows = []
    for arm in probe.ARMS:
        rows.extend(
            [
                _row("corpus", arm, f"{arm}-accept", "accept", "accept"),
                _row("corpus", arm, f"{arm}-reject", "reject", "reject", category="wrong_place"),
            ]
        )
        for index in range(10):
            rows.append(_row("heldout", arm, f"{arm}-positive-{index}", "accept" if index < 9 else "reject", "accept"))
        rows.append(_row("heldout", arm, f"{arm}-negative", "reject", "reject", negative_type="missing"))
    return rows


def test_report_gates_pass_and_fail_each_gate(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": _gate_rows()}), encoding="utf-8")

    assert probe.report_rows(rows_path, report_path) == 0
    report = report_path.read_text(encoding="utf-8")
    assert "C1" in report and "C2" in report and "H1" in report and "H2" in report
    assert "J1m overall: PASS" in report

    failures = {
        "C1": lambda rows: rows.append(_row("corpus", "J1m", "bad-c1", "accept", "reject")),
        "C2": lambda rows: rows.extend(
            _row("corpus", "J1m", f"bad-c2-{index}", "reject", "accept") for index in range(10)
        ),
        "H1": lambda rows: rows.append(_row("heldout", "J1m", "bad-h1", "accept", "reject", negative_type="missing")),
        "H2": lambda rows: None,
    }
    for gate, change in failures.items():
        changed = json.loads(json.dumps(_gate_rows()))
        if gate == "H2":
            for row in changed:
                if row["arm"] == "J1m" and row["set"] == "heldout" and row["case_id"] == "J1m-positive-0":
                    row["relations"][0]["verdict"] = "reject"
        else:
            change(changed)
        rows_path.write_text(json.dumps({"rows": changed}), encoding="utf-8")
        assert probe.report_rows(rows_path, report_path) == 1, gate


def test_no_credential_value_in_dry_run_output(monkeypatch, tmp_path, capsys):
    _install_fixture(monkeypatch, tmp_path)
    secret = "super-secret-j1-token"
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", secret)
    assert probe.main(["--dry-run", "--samples-corpus", "1", "--samples-heldout", "1"]) == 0
    assert secret not in capsys.readouterr().out
