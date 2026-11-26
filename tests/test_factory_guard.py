import json
import subprocess
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from factory.guard import (
    BudgetExhausted,
    CallCap,
    CallResult,
    Caps,
    LimitSleep,
    ModelGuard,
    ModelNotAllowed,
    Overloaded,
    ProviderLimit,
    ProviderPolicy,
    RateLimited,
    SpendLedger,
    Usage,
    guarded_call,
)
from factory.limits import LimitReport, Window, read_claude_stream, read_codex_session

ROOT = Path(__file__).parents[1]
ALLOWLIST = ROOT / "factory" / "config" / "allowlist.json"
NOW = datetime(2026, 1, 31, 23, 30, tzinfo=UTC)


def _guard(tmp_path: Path) -> ModelGuard:
    return ModelGuard.from_file(ALLOWLIST)


def _caps(**overrides: object) -> Caps:
    values: dict[str, object] = {
        "total_budget_usd": 100.0,
        "daily_cap_usd": {},
        "call_caps": [],
        "rate_window_s": 3600,
        "rate_max_usd": 100.0,
    }
    values.update(overrides)
    return Caps(**values)  # type: ignore[arg-type]


def _usage(at: datetime, *, usd: float = 1.0, scene: str = "scene") -> Usage:
    return Usage(at, "claude_code", "claude-opus-5-5", "prose", scene, "ticket", 10, usd)


def _subscription_caps(provider: str = "claude_code") -> Caps:
    return _caps(
        total_budget_usd=0.001,
        daily_cap_usd={},
        rate_max_usd=0.001,
        providers={provider: ProviderPolicy("subscription", {"five_hour": 0.8, "seven_day": 0.8})},
    )


def test_allowlist_loads_with_all_pins() -> None:
    data = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    guard = ModelGuard.from_file(ALLOWLIST)

    assert set(guard.stations) == set(data["stations"])
    for station, pins in data["stations"].items():
        assert [pin.__dict__ for pin in guard.stations[station]] == pins


def test_denied_model_is_refused_at_every_station_even_when_injected(tmp_path: Path) -> None:
    data = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    for pins in data["stations"].values():
        pins.append({"model_id": "claude-fable-5-2", "effort": "high", "provider": "test"})
    config = tmp_path / "allowlist.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    guard = ModelGuard.from_file(config)

    for station in data["stations"]:
        with pytest.raises(ModelNotAllowed):
            guard.check(station, "claude-fable-5-2", "high")


@pytest.mark.parametrize(
    "station",
    [
        pytest.param("prose", id="wrong_effort_is_refused"),
        pytest.param("missing_station", id="unknown_station_is_refused"),
        pytest.param("free_gates", id="script_only_station_refuses_every_model"),
    ],
)
def test_invalid_station_or_effort_is_refused(station: str) -> None:
    with pytest.raises(ModelNotAllowed):
        _guard(Path("unused")).check(station, "claude-opus-5-5", "medium")


def test_total_budget_exhaustion(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    ledger.record(_usage(NOW, usd=10.0))

    with pytest.raises(BudgetExhausted, match="total"):
        guarded_call(
            guard=_guard(tmp_path),
            ledger=ledger,
            caps=_caps(total_budget_usd=10.0),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="ticket-2",
            now=NOW,
            estimate_usd=1.0,
            fn=lambda: CallResult("unused", 1, 1.0),
        )


def test_daily_cap_sleeps_until_next_utc_day_across_month_boundary(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    ledger.record(_usage(NOW, usd=2.0))

    with pytest.raises(LimitSleep) as caught:
        guarded_call(
            guard=_guard(tmp_path),
            ledger=ledger,
            caps=_caps(daily_cap_usd={"claude_code": 2.0}),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="ticket-2",
            now=NOW,
            estimate_usd=1.0,
            fn=lambda: CallResult("unused", 1, 1.0),
        )

    assert caught.value.provider == "claude_code"
    assert caught.value.resume_at == datetime(2026, 2, 1, tzinfo=UTC)


def test_per_scene_and_per_day_call_caps(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    ledger.record(_usage(NOW, scene="scene-a"))
    cap = CallCap("claude_code", "claude-opus-5-5", per_scene_per_day=1, per_day=2)
    common = {
        "guard": _guard(tmp_path),
        "ledger": ledger,
        "caps": _caps(call_caps=[cap]),
        "station": "prose",
        "model_id": "claude-opus-5-5",
        "effort": "high",
        "ticket_id": "ticket-2",
        "now": NOW,
        "estimate_usd": 1.0,
        "fn": lambda: CallResult("unused", 1, 1.0),
    }

    with pytest.raises(LimitSleep):
        guarded_call(scene="scene-a", **common)

    ledger.record(_usage(NOW, scene="scene-b"))
    with pytest.raises(LimitSleep):
        guarded_call(scene="scene-c", **common)


def test_provider_limit_becomes_sleep_and_records_nothing(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    resume_at = datetime(2026, 2, 2, 3, tzinfo=UTC)

    def limited() -> CallResult:
        raise ProviderLimit(resume_at)

    with pytest.raises(LimitSleep) as caught:
        guarded_call(
            guard=_guard(tmp_path),
            ledger=ledger,
            caps=_caps(),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="ticket",
            now=NOW,
            estimate_usd=1.0,
            fn=limited,
        )

    assert caught.value.resume_at == resume_at
    assert ledger.total_usd() == 0


def test_normal_call_records_usage_and_updates_totals(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    result = guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_caps(),
        station="prose",
        model_id="claude-opus-5-5",
        effort="high",
        scene="scene",
        ticket_id="ticket",
        now=NOW,
        fn=lambda: CallResult({"ok": True}, 42, 1.25),
        estimate_usd=1.0,
    )

    assert result.output == {"ok": True}
    assert ledger.total_usd() == 1.25
    assert ledger.day_usd("claude_code", date(2026, 1, 31)) == 1.25
    assert ledger.calls("claude-opus-5-5", date(2026, 1, 31), scene="scene") == 1
    assert ledger._read()[0].estimate_usd == 1.0


def test_rate_of_spend_breaker_names_rate(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    ledger.record(_usage(NOW, usd=3.0))

    with pytest.raises(BudgetExhausted, match="rate"):
        guarded_call(
            guard=_guard(tmp_path),
            ledger=ledger,
            caps=_caps(rate_window_s=60, rate_max_usd=2.0),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="ticket-2",
            now=NOW,
            estimate_usd=1.0,
            fn=lambda: CallResult("unused", 1, 1.0),
        )


def test_corrupt_ledger_line_reports_line_number(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    SpendLedger(path).record(_usage(NOW))
    with path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")

    with pytest.raises(ValueError, match="line 2"):
        SpendLedger(path).total_usd()


def test_ledger_survives_reopening(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    SpendLedger(path).record(
        Usage(NOW, "claude_code", "claude-opus-5-5", "prose", "scene", "ticket", 10, 1.5, estimate_usd=1.25)
    )

    reopened = SpendLedger(path)
    assert reopened.total_usd() == 1.5
    assert reopened.calls("claude-opus-5-5", date(2026, 1, 31)) == 1
    assert reopened._read()[0].estimate_usd == 1.25


def test_old_ledger_row_without_estimate_loads_as_none(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_text(
        json.dumps(
            {
                "at": NOW.isoformat(),
                "provider": "claude_code",
                "model_id": "claude-opus-5-5",
                "station": "prose",
                "scene": "scene",
                "ticket_id": "old",
                "tokens": 3,
                "usd": 1.25,
            }
        )
        + "\n"
    )

    assert SpendLedger(path)._read()[0].estimate_usd is None


def test_reservation_counts_until_settled_and_old_rows_keep_totals(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = SpendLedger(path)
    ledger.record(_usage(NOW, usd=2.0))
    reservation_id = ledger.reserve(
        provider="claude_code",
        model_id="claude-opus-5-5",
        station="prose",
        scene="scene",
        ticket_id="reserved",
        usd=3.0,
        now=NOW,
    )

    assert ledger.total_usd() == 5.0
    assert ledger.day_usd("claude_code", date(2026, 1, 31)) == 5.0
    assert ledger.usd_in_window(NOW, 3600) == 5.0
    assert ledger.open_reservations()[0]["reservation_id"] == reservation_id

    ledger.record(_usage(NOW, usd=1.25), reservation_id=reservation_id)
    assert ledger.total_usd() == 3.25
    assert ledger.open_reservations() == []


def test_reservation_caps_include_open_reservations_and_release_frees_them(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    reservation_id = ledger.reserve(
        provider="claude_code",
        model_id="model",
        station="station",
        scene="scene",
        ticket_id="ticket",
        usd=3.0,
        now=NOW,
        caps=_caps(total_budget_usd=3.0),
    )
    with pytest.raises(BudgetExhausted):
        ledger.reserve(
            provider="claude_code",
            model_id="model",
            station="station",
            scene="scene",
            ticket_id="second",
            usd=0.01,
            now=NOW,
            caps=_caps(total_budget_usd=3.0),
        )
    assert len((tmp_path / "ledger.jsonl").read_text().splitlines()) == 1
    ledger.release(reservation_id)
    assert ledger.total_usd() == 0
    with pytest.raises(ValueError):
        ledger.release(reservation_id)


def test_reservation_daily_cap_and_unknown_or_corrupt_rows(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    with pytest.raises(BudgetExhausted):
        ledger.reserve(
            provider="claude_code",
            model_id="model",
            station="station",
            scene="scene",
            ticket_id="ticket",
            usd=1.01,
            now=NOW,
            caps=_caps(daily_cap_usd={"claude_code": 1.0}),
        )
    assert not ledger.path.exists()
    with pytest.raises(ValueError):
        ledger.release("missing")
    ledger.path.write_text(json.dumps({"kind": "reservation", "reservation_id": "bad"}) + "\n")
    with pytest.raises(ValueError, match="line 1"):
        ledger.total_usd()


def test_crash_left_reservation_is_reopened_and_blocks_spend(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    script = """
from datetime import UTC, datetime
import os
from factory.guard import SpendLedger
ledger = SpendLedger(__import__('sys').argv[1])
ledger.reserve(
    provider='claude_code', model_id='model', station='station', scene='scene',
    ticket_id='ticket', usd=2.0, now=datetime(2026, 1, 31, tzinfo=UTC)
)
os._exit(0)
"""
    subprocess.run(
        ["/home/bcorfman/dev/freytag-forge/.venv/bin/python", "-c", script, str(path)],
        check=True,
        env={"PYTHONPATH": str(ROOT)},
    )
    ledger = SpendLedger(path)
    assert len(ledger.open_reservations()) == 1
    with pytest.raises(BudgetExhausted):
        ledger.reserve(
            provider="claude_code",
            model_id="model",
            station="station",
            scene="scene",
            ticket_id="second",
            usd=0.01,
            now=NOW,
            caps=_caps(total_budget_usd=2.0),
        )


def test_guarded_call_reservation_lifecycle(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    seen: list[int] = []

    def successful() -> CallResult:
        seen.append(len(ledger.open_reservations()))
        return CallResult("ok", 1, 0.5)

    guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_caps(),
        station="prose",
        model_id="claude-opus-5-5",
        effort="high",
        scene="scene",
        ticket_id="success",
        now=NOW,
        estimate_usd=1.0,
        fn=successful,
    )
    assert seen == [1]
    assert ledger.open_reservations() == []

    with pytest.raises(RuntimeError):
        guarded_call(
            guard=_guard(tmp_path),
            ledger=ledger,
            caps=_caps(),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="error",
            now=NOW,
            estimate_usd=1.0,
            fn=lambda: (_ for _ in ()).throw(RuntimeError("unknown billing")),
        )
    assert len(ledger.open_reservations()) == 1


@pytest.mark.parametrize("estimate", [-0.01, True])
def test_usage_rejects_negative_or_boolean_estimate(estimate: object) -> None:
    with pytest.raises(ValueError, match="estimate_usd"):
        Usage(NOW, "claude_code", "claude-opus-5-5", "prose", "scene", "ticket", 1, 1.0, estimate_usd=estimate)


def test_estimate_report_groups_dollar_rows_and_ignores_incomplete_rows(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    ledger.record(Usage(NOW, "provider", "model", "z-station", "scene", "one", 1, 2.0, estimate_usd=1.0))
    ledger.record(Usage(NOW, "provider", "model", "z-station", "scene", "two", 1, 3.0, estimate_usd=2.0))
    ledger.record(Usage(NOW, "provider", "model", "a-station", "scene", "zero", 1, 0.5, estimate_usd=0.0))
    ledger.record(_usage(NOW, usd=4.0))
    ledger.record(
        Usage(NOW, "provider", "model", "ignored", "scene", "subscription", 1, None, "subscription", estimate_usd=1.0)
    )

    assert ledger.estimate_report() == [
        {"station": "a-station", "calls": 1, "estimate_usd": 0.0, "actual_usd": 0.5, "ratio": None},
        {"station": "z-station", "calls": 2, "estimate_usd": 3.0, "actual_usd": 5.0, "ratio": 1.67},
    ]


def test_subscription_usage_keeps_list_price_out_of_dollar_totals(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    report = read_claude_stream((ROOT / "tests/fixtures/factory/claude_stream.jsonl").read_text().splitlines())
    assert report is not None

    guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_subscription_caps(),
        station="prose",
        model_id="claude-opus-5-5",
        effort="high",
        scene="scene",
        ticket_id="subscription",
        now=NOW,
        fn=lambda: CallResult("ok", 42, 0.0028, report),
    )

    usage = ledger._read()[0]
    assert usage.cost_kind == "subscription"
    assert usage.usd is None
    assert usage.list_usd == 0.0028
    assert usage.tokens == 42
    assert ledger.total_usd() == 0


def test_reported_missing_cost_is_unknown(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_caps(),
        station="live_playtest",
        model_id="typesafe/jev",
        effort="none",
        scene="scene",
        ticket_id="unknown",
        now=NOW,
        estimate_usd=1.0,  # Reported providers must reserve before the call.
        fn=lambda: CallResult("ok", 4),
    )

    assert ledger.unknown_cost_rows() == 1
    assert ledger.total_usd() == 0


def test_old_ledger_lines_default_to_dollars(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_text(
        json.dumps(
            {
                "at": NOW.isoformat(),
                "provider": "cloudflare",
                "model_id": "typesafe/jev",
                "station": "live_playtest",
                "scene": "scene",
                "ticket_id": "old",
                "tokens": 3,
                "usd": 1.25,
            }
        )
        + "\n"
    )

    usage = SpendLedger(path)._read()[0]
    assert usage.cost_kind == "dollars"
    assert usage.estimate_usd is None
    assert SpendLedger(path).total_usd() == 1.25


def test_subscription_window_over_ceiling_sleeps_before_call(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    reset = NOW + timedelta(hours=1)
    report = LimitReport("claude_code", (Window("seven_day", 0.81, reset, False),), False, None)
    ledger.record(
        Usage(NOW, "claude_code", "claude-opus-5-5", "prose", "scene", "old", 1, None, "subscription", limits=report)
    )
    called = False

    def fn() -> CallResult:
        nonlocal called
        called = True
        return CallResult("unused", 1)

    with pytest.raises(LimitSleep) as caught:
        guarded_call(
            guard=_guard(tmp_path),
            ledger=ledger,
            caps=_subscription_caps(),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="next",
            now=NOW,
            fn=fn,
        )
    assert caught.value.resume_at == reset
    assert not called


def test_stale_subscription_report_does_not_sleep(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    reset = NOW - timedelta(hours=1)
    report = LimitReport("claude_code", (Window("seven_day", 0.81, reset, False),), False, None)
    ledger.record(
        Usage(NOW, "claude_code", "claude-opus-5-5", "prose", "scene", "old", 1, None, "subscription", limits=report)
    )
    guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_subscription_caps(),
        station="prose",
        model_id="claude-opus-5-5",
        effort="high",
        scene="scene",
        ticket_id="next",
        now=NOW,
        fn=lambda: CallResult("ok", 1),
    )
    assert ledger.calls("claude-opus-5-5", date(2026, 1, 31)) == 2


def test_rate_limited_call_retries_without_duplicate_rows(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    sleeps: list[float] = []
    attempts = 0

    def fn() -> CallResult:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RateLimited()
        return CallResult("ok", 2, 1.0)

    guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_caps(),
        station="prose",
        model_id="claude-opus-5-5",
        effort="high",
        scene="scene",
        ticket_id="retry",
        now=NOW,
        estimate_usd=1.0,
        fn=fn,
        sleep=sleeps.append,
        rand=lambda: 0.0,
    )
    assert attempts == 2
    assert len(sleeps) == 1 and 45 <= sleeps[0] <= 60
    assert len(ledger._read()) == 1


def test_six_rate_limits_raise_after_five_sleeps(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    sleeps: list[float] = []
    with pytest.raises(LimitSleep) as caught:
        guarded_call(
            guard=_guard(tmp_path),
            ledger=ledger,
            caps=_caps(),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="retry",
            now=NOW,
            estimate_usd=1.0,
            fn=lambda: (_ for _ in ()).throw(RateLimited()),
            sleep=sleeps.append,
            rand=lambda: 1.0,
        )
    assert caught.value.provider == "claude_code"
    assert caught.value.resume_at is None
    assert sleeps == [60, 60, 60, 60, 60]
    assert ledger._read() == []


def test_overloaded_call_uses_exponential_retry_delays(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    sleeps: list[float] = []
    attempts = 0

    def fn() -> CallResult:
        nonlocal attempts
        attempts += 1
        if attempts <= 4:
            raise Overloaded()
        return CallResult("ok", 2, 1.0)

    guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_caps(),
        station="prose",
        model_id="claude-opus-5-5",
        effort="high",
        scene="scene",
        ticket_id="retry",
        now=NOW,
        estimate_usd=1.0,
        fn=fn,
        sleep=sleeps.append,
    )
    assert sleeps == [45, 90, 180, 300]


def test_fifth_overload_raises_after_four_sleeps(tmp_path: Path) -> None:
    sleeps: list[float] = []
    with pytest.raises(LimitSleep):
        guarded_call(
            guard=_guard(tmp_path),
            ledger=SpendLedger(tmp_path / "ledger.jsonl"),
            caps=_caps(),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="retry",
            now=NOW,
            estimate_usd=1.0,
            fn=lambda: (_ for _ in ()).throw(Overloaded()),
            sleep=sleeps.append,
        )
    assert sleeps == [45, 90, 180, 300]


def test_provider_limit_report_uses_rejected_window_reset(tmp_path: Path) -> None:
    reset = NOW + timedelta(hours=2)
    report = LimitReport("claude_code", (Window("seven_day", 0.8, reset, True),), False, None)
    with pytest.raises(LimitSleep) as caught:
        guarded_call(
            guard=_guard(tmp_path),
            ledger=SpendLedger(tmp_path / "ledger.jsonl"),
            caps=_subscription_caps(),
            station="prose",
            model_id="claude-opus-5-5",
            effort="high",
            scene="scene",
            ticket_id="limited",
            now=NOW,
            fn=lambda: (_ for _ in ()).throw(ProviderLimit(None, report)),
        )
    assert caught.value.resume_at == reset


def test_codex_credit_drop_is_recorded_as_paid_usage(tmp_path: Path) -> None:
    report = read_codex_session(ROOT / "tests/fixtures/factory/codex_session.jsonl")
    assert report is not None and report.credits is not None
    after = replace(report, credits=report.credits - 1)
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    common = {
        "guard": _guard(tmp_path),
        "ledger": ledger,
        "caps": _subscription_caps("codex"),
        "station": "world_need",
        "model_id": "gpt-5.6-luna",
        "effort": "high",
        "scene": "scene",
        "now": NOW,
    }
    guarded_call(ticket_id="one", fn=lambda: CallResult("ok", 1, None, report), **common)
    guarded_call(ticket_id="two", fn=lambda: CallResult("ok", 1, None, after), **common)
    assert ledger.paid_usage_reasons() == [f"codex credits dropped from {report.credits} to {after.credits}"]


def test_claude_overage_is_recorded_as_paid_usage(tmp_path: Path) -> None:
    report = read_claude_stream((ROOT / "tests/fixtures/factory/claude_stream.jsonl").read_text().splitlines())
    assert report is not None
    overage = replace(report, overage=True)
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_subscription_caps(),
        station="prose",
        model_id="claude-opus-5-5",
        effort="high",
        scene="scene",
        ticket_id="overage",
        now=NOW,
        fn=lambda: CallResult("ok", 1, None, overage),
    )
    assert ledger.paid_usage_reasons() == ["claude_code reports paid overage in use"]


def test_subscription_rows_do_not_trigger_dollar_caps(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    ledger.record(Usage(NOW, "claude_code", "claude-opus-5-5", "prose", "scene", "old", 1, None, "subscription", 999.0))
    guarded_call(
        guard=_guard(tmp_path),
        ledger=ledger,
        caps=_subscription_caps(),
        station="prose",
        model_id="claude-opus-5-5",
        effort="high",
        scene="scene",
        ticket_id="next",
        now=NOW,
        fn=lambda: CallResult("ok", 1, 999.0),
    )
    assert ledger.total_usd() == 0
