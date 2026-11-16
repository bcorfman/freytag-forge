import json
from datetime import UTC, date, datetime
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
    ProviderLimit,
    SpendLedger,
    Usage,
    guarded_call,
)

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


def test_wrong_effort_is_refused() -> None:
    with pytest.raises(ModelNotAllowed):
        _guard(Path("unused")).check("prose", "claude-opus-5-5", "medium")


def test_unknown_station_is_refused() -> None:
    with pytest.raises(ModelNotAllowed):
        _guard(Path("unused")).check("missing_station", "claude-opus-5-5", "medium")


def test_script_only_station_refuses_every_model() -> None:
    with pytest.raises(ModelNotAllowed):
        _guard(Path("unused")).check("free_gates", "claude-opus-5-5", "medium")


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
    )

    assert result.output == {"ok": True}
    assert ledger.total_usd() == 1.25
    assert ledger.day_usd("claude_code", date(2026, 1, 31)) == 1.25
    assert ledger.calls("claude-opus-5-5", date(2026, 1, 31), scene="scene") == 1


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
    SpendLedger(path).record(_usage(NOW, usd=1.5))

    reopened = SpendLedger(path)
    assert reopened.total_usd() == 1.5
    assert reopened.calls("claude-opus-5-5", date(2026, 1, 31)) == 1
