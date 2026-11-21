"""Tests for pure subscription limit readers and decisions."""

import os
from datetime import UTC, datetime
from pathlib import Path

from factory.limits import (
    LimitReport,
    Window,
    find_codex_session,
    paid_usage,
    read_claude_stream,
    read_codex_session,
    window_sleep,
)

FIXTURES = Path(__file__).parent / "fixtures" / "factory"


def test_read_claude_fixture() -> None:
    report = read_claude_stream((FIXTURES / "claude_stream.jsonl").read_text().splitlines())
    assert report is not None
    assert [(window.name, window.used) for window in report.windows] == [("five_hour", 0.1), ("seven_day", 0.19)]
    assert [window.resets_at for window in report.windows] == [
        datetime.fromtimestamp(1795138200, UTC),
        datetime.fromtimestamp(1795442400, UTC),
    ]
    assert report.overage is False
    assert report.credits is None


def test_claude_last_event_wins_and_bad_lines_are_ignored() -> None:
    lines = [
        "not json",
        '{"type":"rate_limit_event","rate_limit_info":{"unifiedWindows":{"old":{"utilization":0.1}}}}',
        '{"type":"rate_limit_event","rate_limit_info":{"isUsingOverage":true,"unifiedWindows":{"new":{"utilization":0.2,"status":"rejected"}}}}',
    ]
    report = read_claude_stream(lines)
    assert report is not None and report.overage is True
    assert report.windows == (Window("new", 0.2, None, True),)
    assert read_claude_stream(["{}", "nope"]) is None


def test_read_codex_fixture() -> None:
    report = read_codex_session(FIXTURES / "codex_session.jsonl")
    assert report is not None
    assert [(window.name, window.used) for window in report.windows] == [("five_hour", 0.04), ("seven_day", 0.06)]
    assert report.credits == 211.72383475
    assert report.overage is None


def test_codex_null_optional_values_and_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    path.write_text(
        'bad\n{"payload":{"rate_limits":{"primary":{"used_percent":100},"secondary":null,"credits":{"balance":null}}}}\n'
    )
    report = read_codex_session(path)
    assert report is not None and report.credits is None
    assert report.windows == (Window("five_hour", 1.0, None, True),)
    empty = tmp_path / "empty.jsonl"
    empty.write_text("not json\n")
    assert read_codex_session(empty) is None


def test_find_codex_session_prefers_latest_nested_match(tmp_path: Path) -> None:
    first = tmp_path / "2026" / "01" / "a-thread.jsonl"
    second = tmp_path / "2026" / "02" / "b-thread.jsonl"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("")
    second.write_text("")
    os.utime(first, (1_700_000_000, 1_700_000_000))
    os.utime(second, (1_700_000_100, 1_700_000_100))
    assert find_codex_session("thread", tmp_path) == second
    assert find_codex_session("missing", tmp_path) is None


def test_window_sleep_decisions() -> None:
    early = datetime(2026, 11, 23, 3, tzinfo=UTC)
    late = datetime(2026, 11, 23, 4, tzinfo=UTC)
    report = LimitReport("codex", (Window("seven_day", 0.91, late, False),), None, None)
    assert window_sleep(report, {"seven_day": 0.92}).sleep is False
    decision = window_sleep(report, {"seven_day": 0.91})
    assert decision.until == late and "seven_day 91% >= ceiling 91%" in decision.reason
    assert window_sleep(LimitReport("x", (Window("other", 0.1, early, True),), None, None), {}).sleep
    both = LimitReport("x", (Window("a", 0.9, early, False), Window("b", 0.8, late, False)), None, None)
    assert window_sleep(both, {"a": 0.9, "b": 0.8}).until == late
    assert window_sleep(LimitReport("x", (Window("a", 1, None, True),), None, None), {}).until is None


def test_paid_usage() -> None:
    before = LimitReport("codex", (), None, 10.0)
    assert paid_usage(None, LimitReport("claude_code", (), True, None)) == "claude_code reports paid overage in use"
    assert paid_usage(before, LimitReport("codex", (), None, 9.0)) == "codex credits dropped from 10.0 to 9.0"
    assert paid_usage(before, LimitReport("codex", (), None, 10.0)) is None
    assert paid_usage(before, LimitReport("codex", (), None, 11.0)) is None
    assert paid_usage(None, LimitReport("codex", (), None, 1.0)) is None
