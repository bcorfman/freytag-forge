import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parents[1] / "scripts/staging_evidence.py"
_SPEC = importlib.util.spec_from_file_location("staging_evidence", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
staging_evidence = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(staging_evidence)


def test_build_evidence_succeeds_when_all_checks_pass():
    evidence = staging_evidence.build_evidence("a" * 40, "https://api.example", "success", "success", "success")

    assert evidence["result"] == "success"
    assert [check["outcome"] for check in evidence["checks"]] == ["success", "success", "success"]


@pytest.mark.parametrize("failed_check", [0, 1, 2])
def test_build_evidence_fails_when_a_check_fails(failed_check):
    outcomes = ["success", "success", "success"]
    outcomes[failed_check] = "failure"

    evidence = staging_evidence.build_evidence("a" * 40, "https://api.example", *outcomes)

    assert evidence["result"] == "failure"
    assert evidence["checks"][failed_check]["outcome"] == "failure"


def test_build_evidence_fails_when_a_check_is_missing():
    evidence = staging_evidence.build_evidence("a" * 40, "", "success", "", "success")

    assert evidence["result"] == "failure"
    assert evidence["checks"][1]["outcome"] == "not-run"


def test_main_writes_evidence_from_environment(monkeypatch, tmp_path):
    report = tmp_path / "nested" / "staging-evaluation.json"
    monkeypatch.setenv("FREYTAG_EVALUATION_REPORT", str(report))
    monkeypatch.setenv("CANDIDATE_SHA", "b" * 40)
    monkeypatch.setenv("API_BASE_URL", "https://staging.example")
    monkeypatch.setenv("API_IDENTITY_OUTCOME", "success")
    monkeypatch.setenv("PAGES_IDENTITY_OUTCOME", "success")
    monkeypatch.setenv("ADAPTER_CONTRACT_OUTCOME", "success")

    staging_evidence.main()

    assert json.loads(report.read_text(encoding="utf-8"))["result"] == "success"
