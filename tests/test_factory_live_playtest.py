import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from factory.guard import LimitSleep
from factory.stations import build_handlers
from factory.stations.live_playtest import (
    _DEFAULTS,
    EARNED_EXIT_CAUSES,
    live_playtest_handler,
    main,
    playtest_summary,
    report_to_packets,
)
from factory.stations.triage import _validate_packet, classify_turns
from factory.tickets import Station, TicketClass

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/factory/blind_player_report_small.json"
NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def report() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def ticket(payload: dict, scene: str = "1A") -> SimpleNamespace:
    return SimpleNamespace(payload=payload, scene=scene, id="stage7")


def clean_report() -> dict:
    value = report()
    value["replicates"] = value["replicates"][:1]
    return value


def write_artifact(root: Path, value: dict) -> Path:
    path = root / "artifacts" / "e2e-blind-player.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    os.utime(path, (NOW.timestamp() + 1, NOW.timestamp() + 1))
    return path


def test_packets_have_triage_shape_and_documented_routes() -> None:
    packets = report_to_packets(report())
    assert [packet["key"] for packet in packets] == ["1A-r2-t1", "1A-r3-t1", "1A-r3-t2"]
    assert set(packets[0]) == {"key", "scene", *_DEFAULTS}
    assert packets[0]["stuck"] is True
    assert packets[1]["match_issues"] == ["narration did not validate"]
    assert packets[2]["stuck"] is False
    assert all(_validate_packet(packet) for packet in packets)
    assert [route["class"] for route in classify_turns(packets)] == [
        TicketClass.STORY_DATA.value,
        "unclear",
        "unclear",
    ]
    assert report_to_packets(clean_report()) == []


def test_packets_cover_rejection_game_break_and_noncommitted_turns() -> None:
    value = clean_report()
    value["replicates"][0]["turns"].extend(
        [
            {"turn": 2, "raw_input": "bad", "text": "", "rejected": True, "rejection": "bad"},
            {"turn": 3, "raw_input": "break", "text": "", "game_break": {"outcome": "timeout"}, "outcome": "committed"},
            {"turn": 4, "raw_input": "uncommitted", "text": "", "outcome": "rejected"},
        ]
    )
    packets = report_to_packets(value, key_prefix="x-")
    assert [packet["key"] for packet in packets] == ["x-1A-r1-t2", "x-1A-r1-t3", "x-1A-r1-t4"]
    assert all(_validate_packet(packet) for packet in packets)
    assert all(route["rule"] == "R9" for route in classify_turns(packets))


def test_summary_and_gate_inputs() -> None:
    summary = playtest_summary(report())
    assert summary["scenes"] == 3
    assert summary["turns"] == 4
    assert summary["stuck_turns"] == 1
    assert summary["rejected"] == 1
    assert summary["game_breaks"] == 1
    assert summary["exit_cause"] == ["play", "none", "forced"]
    assert summary["transition_fired"] == 2
    assert summary["ending_reached"] is False
    assert playtest_summary(clean_report())["runs"][0]["exit_cause"] in EARNED_EXIT_CAUSES


def test_gate_clean_pass_timer_forced_and_empty_fail(tmp_path: Path) -> None:
    handler = live_playtest_handler(tmp_path)
    assert handler(ticket({"report_path": FIXTURE}), NOW).passed is False
    clean_path = tmp_path / "clean.json"
    clean_path.write_text(json.dumps(clean_report()), encoding="utf-8")
    try:
        assert handler(ticket({"report_path": clean_path}), NOW).passed
    finally:
        clean_path.unlink()

    for cause in ("timer", "forced"):
        value = clean_report()
        value["replicates"][0]["exit_cause"] = cause
        value["replicates"][0]["turns"][0]["transition_cause"] = cause
        path = tmp_path / f"stage7-{cause}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        try:
            result = handler(ticket({"report_path": path}), NOW)
            assert not result.passed and result.turns
        finally:
            path.unlink()

    empty = tmp_path / "stage7-empty.json"
    empty.write_text(json.dumps({"replicates": []}), encoding="utf-8")
    try:
        result = handler(ticket({"report_path": empty}), NOW)
        assert not result.passed and result.turns is None
    finally:
        empty.unlink()


def test_saved_handler_pass_failure_and_bad_file(tmp_path: Path) -> None:
    clean = tmp_path / "clean.json"
    clean.write_text(json.dumps(clean_report()), encoding="utf-8")
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps(report()), encoding="utf-8")
    handler = live_playtest_handler(tmp_path)
    passed = handler(ticket({"report_path": clean}), NOW)
    story_failed = handler(ticket({"report_path": failed}), NOW)
    bad = handler(ticket({"report_path": tmp_path / "missing.json"}), NOW)
    assert passed.passed and passed.turns is None
    assert not story_failed.passed and story_failed.turns
    assert not bad.passed and bad.turns is None


def test_live_identity_failures_never_call_runner(monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    calls: list[tuple[dict, int]] = []

    def runner(env, timeout):
        calls.append((env, timeout))
        return subprocess.CompletedProcess([], 0)

    for version, expected in (
        ({"channel": "production", "runtime": "scene-v1", "sha": "abc"}, "abc"),
        ({"channel": "staging", "runtime": "scene-v1", "sha": "other"}, "abc"),
        ({"channel": "staging", "runtime": "scene-v1", "sha": "abc"}, None),
    ):
        handler = live_playtest_handler(
            Path("/tmp"),
            runner=runner,
            fetch_version=lambda _url, version=version: version,
        )
        payload = {"expected_sha": expected}
        result = handler(ticket(payload), NOW)
        assert not result.passed and result.turns is None
    assert calls == []


def test_live_runner_called_once_and_stale_artifact_ignored(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    stale = tmp_path / "artifacts/e2e-blind-player-stale.json"
    stale.parent.mkdir()
    stale.write_text("not json", encoding="utf-8")
    os.utime(stale, (NOW.timestamp() - 10, NOW.timestamp() - 10))
    calls: list[tuple[dict, int]] = []

    def runner(env, timeout):
        calls.append((env, timeout))
        write_artifact(tmp_path, clean_report())
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    result = live_playtest_handler(
        tmp_path,
        runner=runner,
        fetch_version=lambda url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
        now_fn=lambda: NOW,
    )(ticket({"expected_sha": "abc", "scene": "1A", "profile": "raw", "replicates": 3}), NOW)
    assert result.passed
    assert len(calls) == 1
    assert calls[0][0]["E2E_BLIND_SCENE"] == "1A"
    assert calls[0][0]["BLIND_PLAYER_PROFILE"] == "raw"
    assert calls[0][0]["E2E_BLIND_REPLICATES"] == "3"
    assert calls[0][0]["E2E_TURN_TIMEOUT_MS"] == "90000"
    assert calls[0][1] == 7200
    assert not stale.exists()


def test_live_missing_fresh_report_and_default_runner_approval(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    handler = live_playtest_handler(
        tmp_path,
        runner=lambda _env, _timeout: subprocess.CompletedProcess([], 0),
        fetch_version=lambda _url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
        now_fn=lambda: NOW,
    )
    missing = handler(ticket({"expected_sha": "abc"}), NOW)
    assert not missing.passed and missing.turns is None
    refused = live_playtest_handler(
        tmp_path,
        fetch_version=lambda _url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
    )(ticket({"expected_sha": "abc"}), NOW)
    assert not refused.passed and "billed_run_approved" in refused.output and refused.turns is None


def test_quota_raises_provider_limit_without_station_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")

    def runner(_env, _timeout):
        return subprocess.CompletedProcess([], 1, stdout="AI_QUOTA_EXCEEDED", stderr="")

    handler = live_playtest_handler(
        tmp_path,
        runner=runner,
        fetch_version=lambda _url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
        now_fn=lambda: NOW,
    )
    with pytest.raises(LimitSleep) as raised:
        handler(ticket({"expected_sha": "abc"}), NOW)
    assert raised.value.provider == "cloudflare"
    assert raised.value.resume_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_cli_exit_codes_and_build_registration(tmp_path: Path, capsys) -> None:
    clean = tmp_path / "clean.json"
    clean.write_text(json.dumps(clean_report()), encoding="utf-8")
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps(report()), encoding="utf-8")
    assert main(["grade", str(clean)]) == 0
    assert json.loads(capsys.readouterr().out)["packets"] == []
    assert main(["grade", str(failed)]) == 1
    assert json.loads(capsys.readouterr().out)["packets"]
    assert main(["grade", str(tmp_path / "missing.json")]) == 2
    assert Station.LIVE_PLAYTEST in build_handlers(ROOT)
