import json

import pytest

from scripts.ringer.environment_narration import j1_scope_probe as probe
from scripts.ringer.environment_narration import j1_screen_probe as screen


def _case(case_id="s1", *, group="scene_level", kind="positive", negative_type=None, contrast=None):
    place = "the hall" if group == "scene_level" else "the table"
    label = "accept" if kind == "positive" else "reject"
    narration = "Mara sees the lantern." if kind == "positive" else "Mara sees a brass cup."
    return {
        "id": case_id,
        "story": "The Hall Story",
        "scene": "The Hall",
        "scene_place": "the hall",
        "group": group,
        "kind": kind,
        "negative_type": negative_type,
        "contrast": contrast,
        "label": label,
        "narration": narration,
        "relation": {"thing": "lantern", "place": place, "holder": None},
        "note": "fixture",
    }


def _corpus_case(case_id):
    return {
        "id": case_id,
        "story": "Corpus Story",
        "category": "positive_plain",
        "narration": "Mara sees the lantern.",
        "relations": [{"thing": "lantern", "place": "the quay", "holder": None, "label": "accept"}],
        "undetectable_invention": False,
        "note": "fixture",
    }


def _corpus_document():
    return {
        "cases": [_corpus_case("a-022"), _corpus_case("d-009")],
        "combined": "corpus-hash",
        "relation_count": 2,
    }


def _install(monkeypatch, tmp_path, cases=None):
    cases = [_case()] if cases is None else cases
    data = "".join(json.dumps(item) + "\n" for item in cases).encode()
    path = tmp_path / "cases.jsonl"
    path.write_bytes(data)
    monkeypatch.setattr(probe, "CASES_PATH", path)
    monkeypatch.setattr(probe, "LOCK_PATH", tmp_path / "lock.json")
    monkeypatch.setattr(probe, "_validated_corpus", _corpus_document)
    monkeypatch.setattr(probe, "_corpus_lock_matches", lambda corpus: True)
    return path, cases


def _row(set_name, arm, case_id, verdict, label, *, group=None, negative_type=None, score=0.9, sample=0):
    row = {
        "set": set_name,
        "arm": arm,
        "case_id": case_id,
        "sample": sample,
        "story": "The Hall Story",
        "scene": "The Hall",
        "scene_place": "the hall",
        "group": group,
        "category": "positive_plain" if label == "accept" else None,
        "negative_type": negative_type,
        "relations": [{"thing": "lantern", "label": label, "verdict": verdict, "score": score}],
        "latency_ms": 10,
        "jev_model": "jev-1.13.0",
        "jev_version": "observation-relation-v1",
    }
    return row


def _fresh_rows(scene_accepts=60, specific_accepts=60, negative_accepts=0):
    rows = []
    for group, count, accepted in (("scene_level", 12, scene_accepts), ("specific_place", 12, specific_accepts)):
        for index in range(count):
            case_id = f"{group}-positive-{index}"
            for sample in range(5):
                for arm in probe.ARMS:
                    verdict = "accept" if index * 5 + sample < accepted else "reject"
                    rows.append(_row("scope", arm, case_id, verdict, "accept", group=group, sample=sample))
    for index in range(36):
        case_id = f"negative-{index}"
        for sample in range(5):
            for arm in probe.ARMS:
                verdict = "accept" if index * 5 + sample < negative_accepts else "reject"
                rows.append(
                    _row(
                        "scope",
                        arm,
                        case_id,
                        verdict,
                        "reject",
                        group="scene_level" if index < 18 else "specific_place",
                        negative_type="lookalike" if index < 24 else "missing",
                        score=0.7 if verdict == "accept" else 0.1,
                        sample=sample,
                    )
                )
    return rows


def _carried(tmp_path, *, model="jev-1.13.0"):
    rows = [
        {
            "set": "corpus",
            "arm": "V0",
            "case_id": "old-reject",
            "category": "wrong_place",
            "latency_ms": 10,
            "jev_model": model,
            "jev_version": "observation-relation-v1",
            "relations": [{"thing": "cup", "label": "reject", "verdict": "reject", "score": 0.1}],
        },
        {
            "set": "corpus",
            "arm": "V0",
            "case_id": "old-accept",
            "category": "positive_plain",
            "latency_ms": 10,
            "jev_model": model,
            "jev_version": "observation-relation-v1",
            "relations": [{"thing": "cup", "label": "accept", "verdict": "accept", "score": 0.9}],
        },
    ]
    path = tmp_path / "carried.json"
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    return path


def test_j1c_rule_and_payload_selection():
    scene = _case()
    specific = _case("specific", group="specific_place")
    assert probe.j1c_arm(scene) == "J1m"
    assert probe.j1c_arm(specific) == "V0"
    assert probe._request_payload(scene, "J1m", "heldout") == probe._request_payload(scene, "J1m", "heldout")
    assert probe._request_payload(specific, probe.j1c_arm(specific), "heldout") == screen._request_payload(
        specific, "V0", "heldout"
    )
    assert probe._request_payload(scene, probe.j1c_arm(scene), "heldout") == screen._request_payload(
        scene, "J1m", "heldout"
    )
    assert (
        screen._request_payload(scene, "V0", "heldout")["input"]["questions"]
        == screen._request_payload(scene, "J1m", "heldout")["input"]["questions"]
    )


def test_validate_good_and_each_validation_rule(monkeypatch, tmp_path, capsys):
    cases = [_case()]
    _install(monkeypatch, tmp_path, cases)
    monkeypatch.setattr(probe, "_corpus_lock_matches", lambda corpus: True)
    assert probe.main(["--validate"]) == 0
    assert "scene_level" in capsys.readouterr().out

    invalid_cases = [
        {**_case(), "extra": True},
        {**_case(), "kind": "negative", "label": "accept"},
        {**_case(), "kind": "negative", "negative_type": "unknown", "label": "reject"},
        {**_case(), "negative_type": "missing"},
        {**_case(), "contrast": False},
        {**_case(), "group": "specific_place"},
        {**_case(), "narration": "Mara crosses the hall."},
        {
            **_case(),
            "kind": "negative",
            "label": "reject",
            "negative_type": "missing",
            "narration": "The lantern is absent.",
        },
    ]
    for invalid in invalid_cases:
        path = tmp_path / "bad.jsonl"
        path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
        monkeypatch.setattr(probe, "CASES_PATH", path)
        assert probe.main(["--validate"]) == 1


def test_lock_then_run_refuses_changed_fixture(monkeypatch, tmp_path, capsys):
    path, _ = _install(monkeypatch, tmp_path, [_case("a")])
    assert probe.main(["--lock"]) == 0
    path.write_text(json.dumps(_case("changed")) + "\n", encoding="utf-8")
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "worker")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "token")
    assert probe.main(["--run", "--confirm", "--samples", "1", "--out", str(tmp_path / "rows")]) == 2
    assert "matching lock" in capsys.readouterr().err


def test_planned_call_arithmetic_and_seeded_order():
    cases = [_case("a"), _case("b")]
    regressions = [_corpus_case("a-022"), _corpus_case("d-009")]
    assert probe._planned_count(60, 2, 5) == 620
    first = probe._planned_calls(cases, regressions, samples=2)
    assert first == probe._planned_calls(cases, regressions, samples=2)
    assert [(item["set"], item["arm"], item["sample"]) for item in first[:4]] == [
        ("scope", "V0", 0),
        ("scope", "J1m", 0),
        ("scope", "V0", 0),
        ("scope", "J1m", 0),
    ]


@pytest.mark.parametrize(
    "arguments, expected",
    [
        (["--run"], "requires --confirm"),
        (["--run", "--confirm"], "requires --out"),
        (["--run", "--confirm", "--max-calls", "3"], "exceed --max-calls"),
        (["--run", "--confirm", "--max-usd", "0"], "exceeds --max-usd"),
    ],
)
def test_run_refusals(monkeypatch, tmp_path, capsys, arguments, expected):
    _install(monkeypatch, tmp_path, [_case()])
    monkeypatch.setattr(probe, "_ceiling", lambda *args: 0.01)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "worker")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "token")
    args = arguments + ["--samples", "1"]
    if expected != "requires --out":
        args += ["--out", str(tmp_path / "rows")]
    assert probe.main(args) == 2
    assert expected in capsys.readouterr().err


def test_run_refuses_missing_environment(monkeypatch, tmp_path, capsys):
    _install(monkeypatch, tmp_path, [_case()])
    monkeypatch.setattr(probe, "_lock_matches", lambda *args: True)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    assert probe.main(["--run", "--confirm", "--samples", "1", "--out", str(tmp_path / "rows")]) == 2
    assert "CLOUDFLARE_WORKER_URL" in capsys.readouterr().err


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


def test_fake_client_run_atomic_completion_and_unusable_stop(tmp_path):
    output = tmp_path / "rows.json"
    document = probe.run_cases(
        [_case()],
        [_corpus_case("a-022"), _corpus_case("d-009")],
        samples=1,
        max_calls=6,
        out=output,
        client=FakeClient(),
        cases_hash="cases-hash",
        corpus_hash="corpus-hash",
    )
    assert len(document["rows"]) == 6
    assert json.loads(output.read_text())["stop_reason"] is None

    class Unusable(FakeClient):
        def ask(self, state, questions):
            self.calls.append((state, questions))
            return None

    stopped = probe.run_cases(
        [_case("a"), _case("b")],
        [],
        samples=2,
        max_calls=4,
        out=tmp_path / "stopped.json",
        client=Unusable(),
        cases_hash="cases-hash",
        corpus_hash="corpus-hash",
    )
    assert len(stopped["rows"]) == 3
    assert stopped["stop_reason"] == "three_consecutive_unusable"


def test_fake_client_exception_leaves_incomplete_document(tmp_path):
    output = tmp_path / "rows.json"
    with pytest.raises(RuntimeError) as error:
        probe.run_cases(
            [_case()],
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


def test_report_passes_and_fails_each_f_gate(tmp_path):
    carried = _carried(tmp_path)
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows = _fresh_rows()
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path, carried) == 0
    report = report_path.read_text()
    assert "F1" in report and "F2" in report and "F3" in report

    for mutation in (
        lambda current: current.append(_row("scope", "J1m", "bad", "accept", "reject", group="scene_level")),
        lambda current: current.append(
            _row("scope", "J1m", "scene_level-positive-0", "reject", "accept", group="scene_level")
        ),
        lambda current: current.append(
            _row("scope", "V0", "specific_place-positive-0", "reject", "accept", group="specific_place")
        ),
    ):
        changed = json.loads(json.dumps(rows))
        mutation(changed)
        rows_path.write_text(json.dumps({"rows": changed}), encoding="utf-8")
        assert probe.report_rows(rows_path, report_path, carried) == 1


def test_report_carried_void_and_missing_file(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": _fresh_rows()}), encoding="utf-8")
    mismatch = _carried(tmp_path, model="different-model")
    assert probe.report_rows(rows_path, report_path, mismatch) == 1
    assert "carried gates void: Jev model changed" in report_path.read_text()
    missing = tmp_path / "missing.json"
    assert probe.report_rows(rows_path, report_path, missing) == 1
    assert "carried gates: rows file missing" in report_path.read_text()


def test_no_credential_value_in_dry_run_output(monkeypatch, tmp_path, capsys):
    cases = [_case(f"case-{index}") for index in range(60)]
    _install(monkeypatch, tmp_path, cases)
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "super-secret-scope-token")
    assert probe.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "super-secret-scope-token" not in output
    assert "planned requests:" in output and "= 620" in output
