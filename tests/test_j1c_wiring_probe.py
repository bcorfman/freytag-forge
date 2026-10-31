import json

import pytest

from scripts.ringer.environment_narration import j1_scope_probe as scope
from scripts.ringer.environment_narration import j1c_wiring_probe as probe

CASES_PATH = probe.CASES_PATH


def _real_cases():
    return scope._validated_cases(CASES_PATH)[0]


def _fixture_case(case_id="f-1-01", *, group="scene_level", label="accept", thing="lantern"):
    place = "the hall" if group == "scene_level" else "the table"
    scene_place = "the hall"
    return {
        "id": case_id,
        "story": "Hall Story",
        "scene": "Evening Hall",
        "scene_place": scene_place,
        "group": group,
        "kind": "positive" if label == "accept" else "negative",
        "negative_type": None if label == "accept" else "missing",
        "contrast": None,
        "label": label,
        "narration": "Mara sees a brass cup.",
        "relation": {"thing": thing, "place": place, "holder": None},
        "note": "fixture",
    }


def _install(monkeypatch, tmp_path, cases=None, *, lock=True):
    cases = _real_cases() if cases is None else cases
    cases_path = tmp_path / "cases.jsonl"
    data = "".join(json.dumps(case) + "\n" for case in cases).encode()
    cases_path.write_bytes(data)
    lock_path = tmp_path / "lock.json"
    monkeypatch.setattr(probe, "CASES_PATH", cases_path)
    monkeypatch.setattr(probe, "LOCK_PATH", lock_path)
    monkeypatch.setattr(scope, "CASES_PATH", cases_path)
    monkeypatch.setattr(scope, "LOCK_PATH", lock_path)
    monkeypatch.setattr(probe, "_lock_matches", lambda *args: lock)
    monkeypatch.setattr(probe, "_validated_corpus", lambda: {"combined": "corpus-hash"})
    return cases_path, data


def _row(set_name, request_id, arm, sample, relations, *, state_differed=True, latency=10):
    return {
        "set": set_name,
        "request_id": request_id,
        "arm": arm,
        "sample": sample,
        "relations": relations,
        "j1c_state_differed": state_differed,
        "latency_ms": latency,
        "jev_model": "fake-model",
        "jev_version": "fake-version",
    }


def _relation(thing, label, scene_level, verdict="reject", score=0.1):
    return {
        "thing": thing,
        "label": label,
        "scene_level": scene_level,
        "verdict": verdict,
        "score": score,
    }


def _report_rows(*, a1=True, a2=True, b1=True, b2=True, b3=True):
    rows = []
    for index in range(30):
        label = "accept" if index < 12 else "reject"
        for sample in range(5):
            for arm in probe.ARMS:
                verdict = "reject"
                if label == "accept" and a2 and index < 12 and sample < 5:
                    verdict = "accept"
                if label == "reject" and not a1 and index == 12 and sample == 0 and arm == "J1c":
                    verdict = "accept"
                rows.append(
                    _row(
                        "A",
                        f"a-{index}",
                        arm,
                        sample,
                        [_relation("thing", label, True, verdict, 0.9 if verdict == "accept" else 0.1)],
                    )
                )
    for index in range(6):
        request_id = f"m-{index + 1}-1"
        for sample in range(5):
            for arm in probe.ARMS:
                relations = [
                    _relation(
                        "thing",
                        "accept",
                        True,
                        "accept" if b2 else "reject",
                        0.9,
                    ),
                    _relation(
                        "thing",
                        "accept",
                        False,
                        "accept" if b2 else "reject",
                        0.9,
                    ),
                ]
                if not b3 and index == 0 and arm == "J1c":
                    relations[1]["verdict"] = "reject"
                rows.append(_row("B", request_id, arm, sample, relations))
    for index in range(3):
        request_id = f"m-{index + 1}-2"
        for sample in range(5):
            for arm in probe.ARMS:
                relations = [
                    _relation("thing", "accept", True, "accept" if b2 else "reject", 0.9),
                    _relation("thing", "reject", False, "reject", 0.1),
                ]
                if not b1 and index == 0 and sample == 0 and arm == "J1c":
                    relations[1]["verdict"] = "accept"
                rows.append(_row("B", request_id, arm, sample, relations))
    for index in range(3):
        request_id = f"m-{index + 4}-3"
        for sample in range(5):
            for arm in probe.ARMS:
                relations = [
                    _relation("thing", "accept", False, "accept" if b2 else "reject", 0.9),
                    _relation("thing", "reject", True, "reject", 0.1),
                ]
                if not b1 and index == 0 and sample == 0 and arm == "J1c":
                    relations[1]["verdict"] = "accept"
                rows.append(_row("B", request_id, arm, sample, relations))
    return rows


def test_label_and_j1c_state_variants():
    assert probe.label("the mountain observatory") == "Mountain observatory"
    assert probe.label("The Orchard") == "Orchard"
    assert probe.label("harbor") == "Harbor"
    assert probe.j1c_state("text", [("lantern", "Hall", True)], "Hall") == {
        "narration": "text",
        "scene": "Hall",
        "starting_places": {"lantern": "Hall"},
    }
    assert probe.j1c_state("text", [("lantern", "Table", False)], "Hall") == {"narration": "text"}
    assert probe.j1c_state("text", [("lantern", "Hall", True), ("cup", "Table", False)], "Hall") == {
        "narration": "text",
        "scene": "Hall",
        "starting_places": {"lantern": "Hall"},
    }


def test_set_derivation_counts_labels_and_reject_guard():
    cases = _real_cases()
    set_a, set_b = probe.build_sets(cases)
    assert len(set_a) == 30
    assert len(set_b) == 12
    assert sum(relation["label"] == "accept" for request in set_b for relation in request["relations"]) == 18
    assert sum(relation["label"] == "reject" for request in set_b for relation in request["relations"]) == 6
    by_id = {request["request_id"]: request for request in set_b}
    assert [relation["label"] for relation in by_id["m-1-1"]["relations"]] == ["accept", "accept"]
    assert [relation["label"] for relation in by_id["m-2-2"]["relations"]] == ["accept", "reject"]
    assert [relation["label"] for relation in by_id["m-4-3"]["relations"]] == ["accept", "reject"]

    doctored = [dict(case) for case in cases]
    doctored_case = next(case for case in doctored if case["id"] == "f-1-02")
    reject_case = next(case for case in doctored if case["id"] == "f-1-10")
    doctored_case["narration"] = reject_case["relation"]["thing"]
    with pytest.raises(ValueError) as error:
        probe.build_sets(doctored)
    assert "reject-labelled" in str(error.value)


def test_build_sets_rejects_missing_referenced_case():
    cases = _real_cases()
    with pytest.raises(ValueError) as error:
        probe.build_sets([case for case in cases if case["id"] != "f-1-10"])
    assert "f-1-10" in str(error.value)


def test_planned_call_arithmetic_and_seeded_order():
    set_a, set_b = probe.build_sets(_real_cases())
    assert probe.planned_count(set_a, set_b, 5) == 420
    first = probe.planned_calls(set_a, set_b, samples=2)
    assert first == probe.planned_calls(set_a, set_b, samples=2)
    assert [(item["set"], item["arm"], item["sample"]) for item in first[:4]] == [
        ("A", "V0", 0),
        ("A", "J1c", 0),
        ("A", "V0", 0),
        ("A", "J1c", 0),
    ]


@pytest.mark.parametrize(
    "arguments, expected",
    [
        (["--run"], "requires --confirm"),
        (["--run", "--confirm"], "requires --out"),
        (["--run", "--confirm", "--max-calls", "419"], "exceed --max-calls"),
        (["--run", "--confirm", "--max-usd", "0"], "exceeds --max-usd"),
    ],
)
def test_run_refusals(monkeypatch, tmp_path, capsys, arguments, expected):
    _install(monkeypatch, tmp_path)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "worker")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "token")
    args = arguments + ["--samples", "5"]
    if expected != "requires --out":
        args += ["--out", str(tmp_path / "rows.json")]
    assert probe.main(args) == 2
    assert expected in capsys.readouterr().err


def test_run_refuses_bad_lock_and_missing_environment(monkeypatch, tmp_path, capsys):
    _install(monkeypatch, tmp_path, lock=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "worker")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "token")
    assert probe.main(["--run", "--confirm", "--samples", "5", "--out", str(tmp_path / "rows")]) == 2
    assert "matching lock" in capsys.readouterr().err

    _install(monkeypatch, tmp_path, lock=True)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    assert probe.main(["--run", "--confirm", "--samples", "5", "--out", str(tmp_path / "rows")]) == 2
    assert "CLOUDFLARE_WORKER_URL" in capsys.readouterr().err


class FakeClient:
    last_model = "fake-model"
    last_version = "fake-version"
    last_status = 200

    def __init__(self, answer=None, unusable=False, raise_after=None):
        self.answer = answer or {"relation_0": {"noul": 0.9}, "relation_1": {"noul": 0.9}}
        self.unusable = unusable
        self.raise_after = raise_after
        self.calls = []

    def ask(self, state, questions):
        if self.raise_after is not None and len(self.calls) >= self.raise_after:
            raise RuntimeError("fake failure")
        self.calls.append((state, questions))
        return None if self.unusable else self.answer


def test_fake_client_run_completion_unusable_stop_and_exception(tmp_path):
    set_a, set_b = probe.build_sets(_real_cases())
    output = tmp_path / "rows.json"
    document = probe.run_requests(
        set_a,
        set_b,
        samples=5,
        max_calls=420,
        out=output,
        client=FakeClient(),
        cases_hash="cases-hash",
        corpus_hash="corpus-hash",
    )
    assert len(document["rows"]) == 420
    assert json.loads(output.read_text())["stop_reason"] is None
    assert all(row["request_id"] for row in document["rows"])

    stopped = probe.run_requests(
        set_a[:2],
        [],
        samples=2,
        max_calls=8,
        out=tmp_path / "stopped.json",
        client=FakeClient(unusable=True),
        cases_hash="cases-hash",
        corpus_hash="corpus-hash",
    )
    assert len(stopped["rows"]) == 3
    assert stopped["stop_reason"] == "three_consecutive_unusable"

    output = tmp_path / "incomplete.json"
    with pytest.raises(RuntimeError) as error:
        probe.run_requests(
            set_a[:1],
            [],
            samples=2,
            max_calls=2,
            out=output,
            client=FakeClient(raise_after=1),
            cases_hash="cases-hash",
            corpus_hash="corpus-hash",
        )
    assert str(error.value) == "fake failure"
    assert json.loads(output.read_text())["stop_reason"] == "incomplete"


def test_report_passes_and_each_gate_failure(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows = _report_rows()
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path) == 0
    report = report_path.read_text()
    assert all(gate in report and f"{gate}: PASS" in report for gate in ("A1", "A2", "B1", "B2", "B3"))

    failures = (
        ("A1", {"a1": False}),
        ("A2", {"a2": False}),
        ("B1", {"b1": False}),
        ("B2", {"b2": False}),
        ("B3", {"b3": False}),
    )
    for gate, kwargs in failures:
        rows_path.write_text(json.dumps({"rows": _report_rows(**kwargs)}), encoding="utf-8")
        assert probe.report_rows(rows_path, report_path) == 1
        assert f"{gate}: FAIL" in report_path.read_text()


def test_dry_run_redacts_credential_and_validate_prints_counts(monkeypatch, tmp_path, capsys):
    _install(monkeypatch, tmp_path)
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "super-secret-token")
    assert probe.main(["--validate"]) == 0
    assert "Set A: 30" in capsys.readouterr().out
    assert probe.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "super-secret-token" not in output
    assert "planned requests:" in output and "= 420" in output


def test_report_failures_return_one(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path)
    assert probe.main(["--report", "--rows", str(tmp_path / "missing.json"), "--out", str(tmp_path / "report.md")]) == 1

    _install(monkeypatch, tmp_path, lock=False)
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps({"rows": []}), encoding="utf-8")
    assert probe.main(["--report", "--rows", str(rows), "--out", str(tmp_path / "report.md")]) == 1
