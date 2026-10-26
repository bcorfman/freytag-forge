from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import baseline


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("network access is forbidden")

    def fail_urlopen(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("urllib network access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_socket)
    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)


def _run(out: Path) -> None:
    baseline.main(["--out", str(out)])


def _load(out: Path) -> dict[str, object]:
    return json.loads(out.read_text())


def test_output_is_byte_identical_across_two_runs(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    _run(first)
    _run(second)

    assert first.read_bytes() == second.read_bytes()


def test_schema_and_case_order(tmp_path: Path) -> None:
    output = tmp_path / "baseline.json"
    _run(output)
    payload = _load(output)

    assert payload["schema"] == 1
    assert [case["id"] for case in payload["cases"]] == [
        "boarding_go_to_truck",
        "boarding_get_in",
        "boarding_enter_truck",
        "boarding_from_kitchen",
        "already_seated",
        "compound_enter_and_inspect",
        "approach_truck",
        "look_around_outside",
    ]


def test_consumed_boarding_cases_capture_the_current_omission(tmp_path: Path) -> None:
    output = tmp_path / "baseline.json"
    _run(output)
    cases = {case["id"]: case for case in _load(output)["cases"]}

    for case_id in (
        "boarding_go_to_truck",
        "boarding_get_in",
        "boarding_enter_truck",
        "boarding_from_kitchen",
    ):
        case = cases[case_id]
        assert case["engine_text_turn"] is True
        assert case["command_consumed"] is True
        assert case["things_names"] == ["Kristin"]
        assert case["laptop_only_in_background_line"] is True
        assert case["omissions"] == ["Kristin's laptop"]


def test_non_consumed_cases_and_already_seated_are_recorded(tmp_path: Path) -> None:
    output = tmp_path / "baseline.json"
    _run(output)
    cases = {case["id"]: case for case in _load(output)["cases"]}

    for case_id in ("approach_truck", "look_around_outside"):
        assert cases[case_id]["engine_text_turn"] is False
        assert cases[case_id]["omissions"] == []

    assert cases["compound_enter_and_inspect"]["command_consumed"] is False
    assert "already" in cases["already_seated"]["engine_text"]


def test_missing_historical_artifact_is_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "does-not-exist.json"
    monkeypatch.setattr(baseline, "HISTORICAL_ARTIFACT_PATHS", (missing,))
    output = tmp_path / "baseline.json"

    _run(output)

    artifacts = _load(output)["historical_artifacts"]
    assert artifacts[0] == {"path": str(missing), "exists": False, "sha256": None}
    assert artifacts[-1]["path"] == baseline.HISTORICAL_GIT_OBJECT


def test_worker_default_model_parse_accepts_configured_model_name() -> None:
    source = 'const configuredModel = asString(env.CF_AI_MODEL).trim() || "@cf/meta/llama-3.1-8b-instruct-fast";'

    assert baseline.parse_worker_default_model(source) == "@cf/meta/llama-3.1-8b-instruct-fast"


def test_worker_default_model_parse_accepts_model_name() -> None:
    source = 'const model = asString(env.CF_AI_MODEL).trim() || "@cf/meta/llama-3.1-8b-instruct-fast";'

    assert baseline.parse_worker_default_model(source) == "@cf/meta/llama-3.1-8b-instruct-fast"


def test_worker_default_model_parse_fails_loudly_without_a_default() -> None:
    with pytest.raises(RuntimeError, match="default model"):
        baseline.parse_worker_default_model('const model = "not the default";')
