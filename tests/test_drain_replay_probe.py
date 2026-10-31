import hashlib
import json

import pytest

from scripts.ringer.environment_narration import drain_replay_probe as probe


def _real_cases():
    return probe._validated_cases()[0]


def _install(monkeypatch, tmp_path):
    cases = _real_cases()
    path = tmp_path / "cases.jsonl"
    data = probe.CASES_PATH.read_bytes()
    path.write_bytes(data)
    monkeypatch.setattr(probe, "CASES_PATH", path)
    monkeypatch.setattr(probe, "CASES_SHA256", hashlib.sha256(data).hexdigest())
    return cases, path


def test_validate_detects_an_edited_case_via_the_lock(monkeypatch, tmp_path, capsys):
    _cases, path = _install(monkeypatch, tmp_path)
    assert probe.main(["--validate"]) == 0
    assert "cases lock: matching" in capsys.readouterr().out

    edited = path.read_text(encoding="utf-8").replace("valid-hidden-first", "edited-case", 1)
    path.write_text(edited, encoding="utf-8")
    assert probe.main(["--validate"]) == 1
    assert "cases lock: mismatch" in capsys.readouterr().out


def test_dry_run_counts_sixty_calls_and_refuses_caps(monkeypatch, tmp_path, capsys):
    _install(monkeypatch, tmp_path)
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "secret-token")
    assert probe.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "planned calls: 60" in output
    assert "secret-token" not in output
    assert probe.main(["--dry-run", "--max-calls", "59"]) == 2
    assert "exceed --max-calls" in capsys.readouterr().err
    assert probe.main(["--dry-run", "--max-usd", "0"]) == 2
    assert "exceeds --max-usd" in capsys.readouterr().err


def test_run_requires_confirmation_before_credentials(monkeypatch, tmp_path, capsys):
    _install(monkeypatch, tmp_path)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    assert probe.main(["--run", "--out", str(tmp_path / "rows.json")]) == 2
    assert "requires --confirm" in capsys.readouterr().err


def test_payload_shapes_and_questions_are_shared_between_arms():
    case = _real_cases()[0]
    v0 = probe._payload(case, "V0")
    j1c = probe._payload(case, "J1c")
    assert v0["state"] == {"narration": case["narration"]}
    assert j1c["state"] == {
        "narration": case["narration"],
        "scene": "Los Angeles park",
        "starting_places": {"storm drain": "Los Angeles park"},
    }
    assert v0["questions"] == j1c["questions"]


class FakeClient:
    last_model = "fake-model"
    last_version = "fake-version"

    def __init__(self, answer=None, status=200):
        self.answer = answer if answer is not None else {"relation_0": {"noul": 0.7}}
        self.last_status = status
        self.calls = []

    def ask(self, state, questions):
        self.calls.append((state, questions))
        return self.answer


def test_fake_ask_uses_scene_state_for_j1c(tmp_path):
    cases = _real_cases()[:1]
    client = FakeClient()
    document = probe.run_cases(
        cases,
        samples=1,
        max_calls=2,
        out=tmp_path / "rows.json",
        client=client,
        cases_hash="test-hash",
    )
    assert len(document["rows"]) == 2
    assert client.calls[0][0] == {"narration": cases[0]["narration"]}
    assert client.calls[1][0] == {
        "narration": cases[0]["narration"],
        "scene": "Los Angeles park",
        "starting_places": {"storm drain": "Los Angeles park"},
    }


def test_run_stops_on_the_first_429_and_keeps_partial_rows(tmp_path):
    client = FakeClient(answer=None, status=429)
    client.answer = None
    document = probe.run_cases(
        _real_cases(),
        samples=5,
        max_calls=60,
        out=tmp_path / "rows.json",
        client=client,
        cases_hash="test-hash",
    )
    assert len(document["rows"]) == 1
    assert document["stop_reason"] == "http_429"
    assert json.loads((tmp_path / "rows.json").read_text())["stop_reason"] == "http_429"


def _report_document(cases):
    rows = []
    call_index = 0
    for case in cases:
        for sample in range(5):
            for arm in probe.ARMS:
                call_index += 1
                accepted = arm == "J1c" and (case["location_valid"] or case["id"] == "problematic-ajar")
                if case["id"] == "valid-hedge-first" and arm == "J1c" and sample == 4:
                    accepted = False
                rows.append(
                    {
                        "call_index": call_index,
                        "case_id": case["id"],
                        "sample": sample,
                        "arm": arm,
                        "location_valid": case["location_valid"],
                        "condition_policy": case["condition_policy"],
                        "relation": {"verdict": "accept" if accepted else "reject", "score": 0.8},
                    }
                )
    return {
        "schema": 1,
        "mode": "run",
        "samples": 5,
        "calls_planned": 60,
        "rows": rows,
        "stop_reason": None,
        "cases_sha256": probe._sha256(probe.CASES_PATH.read_bytes()),
    }


def test_report_applies_rules_and_handles_a_partial_run(tmp_path):
    cases = _real_cases()
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps(_report_document(cases)), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path) == 0
    report = report_path.read_text(encoding="utf-8")
    assert "Overall: PASS" in report
    assert "location accepted / condition not judged" in report

    partial = _report_document(cases)
    partial["rows"] = partial["rows"][:1]
    partial["stop_reason"] = "http_429"
    rows_path.write_text(json.dumps(partial), encoding="utf-8")
    assert probe.report_rows(rows_path, report_path) == 1
    assert "Run completeness: partial" in report_path.read_text(encoding="utf-8")


def test_report_rejects_a_changed_cases_hash(tmp_path):
    rows_path = tmp_path / "rows.json"
    report_path = tmp_path / "report.md"
    rows_path.write_text(json.dumps({"rows": [], "cases_sha256": "wrong"}), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        probe.report_rows(rows_path, report_path)
    assert "does not match" in str(error.value)
