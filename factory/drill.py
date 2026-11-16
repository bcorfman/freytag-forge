"""Deterministic circuit-breaker drills for the dark factory."""

from __future__ import annotations

import contextlib
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import factory.breakers as breakers
from factory.guard import Caps, SpendLedger, Usage
from factory.state import FactoryState
from factory.tickets import Station, Status, Ticket, TicketQueue

BREAKER_NAMES: tuple[str, ...] = (
    "budget_spent",
    "spend_rate",
    "repeat_failure",
    "token_outlier",
    "provider_overdue",
    "canary_passed",
    "harness_changed",
    "crash",
)


@dataclass(frozen=True)
class DrillResult:
    """The outcome and evidence for one breaker drill."""

    name: str
    passed: bool
    detail: str


def _ticket(ticket_id: str, now: datetime, *, status: Status = Status.QUEUED, tokens: int = 0) -> Ticket:
    stamp = now.isoformat()
    return Ticket(
        id=ticket_id,
        scene="drill",
        station=Station.PROSE,
        token_budget=1000,
        created_at=stamp,
        updated_at=stamp,
        status=status,
        tokens_used=tokens,
    )


def _caps_for(name: str) -> Caps:
    if name == "budget_spent":
        return Caps(total_budget_usd=1.0, daily_cap_usd={}, call_caps=[], rate_window_s=3600, rate_max_usd=100.0)
    if name == "spend_rate":
        return Caps(total_budget_usd=100.0, daily_cap_usd={}, call_caps=[], rate_window_s=3600, rate_max_usd=1.0)
    return Caps(total_budget_usd=100.0, daily_cap_usd={}, call_caps=[], rate_window_s=3600, rate_max_usd=100.0)


def _record_spend(ledger: SpendLedger, now: datetime, usd: float, ticket_id: str) -> None:
    ledger.record(
        Usage(
            at=now,
            provider="drill-provider",
            model_id="drill-model",
            station="drill",
            scene="drill",
            ticket_id=ticket_id,
            tokens=1,
            usd=usd,
        )
    )


def _inject_fault(
    name: str,
    *,
    queue: TicketQueue,
    state: FactoryState,
    ledger: SpendLedger,
    config: breakers.BreakerConfig,
    caps: Caps,
    now: datetime,
) -> tuple[tuple[str, ...], frozenset[str]]:
    """Inject one named fault and return the extra breaker arguments it needs."""

    if name == "budget_spent":
        _record_spend(ledger, now, caps.total_budget_usd, "budget")
    elif name == "spend_rate":
        _record_spend(ledger, now, caps.rate_max_usd + 0.01, "rate")
    elif name == "repeat_failure":
        queue.add(_ticket("repeat", now))
        for _ in range(config.repeat_failures):
            queue.record_failure("repeat", "drill-check", "same output", now, max_attempts=10)
    elif name == "token_outlier":
        for index in range(config.min_tickets_for_median):
            ticket_id = f"normal-{index}"
            queue.add(_ticket(ticket_id, now))
            queue.record_tokens(ticket_id, 10)
        queue.add(_ticket("outlier", now))
        queue.record_tokens("outlier", 51)
    elif name == "provider_overdue":
        state.sleep_lane(
            "drill-provider",
            now - timedelta(seconds=config.provider_overdue_s),
        )
    elif name == "canary_passed":
        queue.add(_ticket("canary", now))
        queue.record_pass("canary", now)
        return (), frozenset({"canary"})
    elif name == "harness_changed":
        return ("factory/guard.py",), frozenset()
    elif name == "crash":
        return (), frozenset()
    else:
        raise ValueError(f"unknown breaker {name!r}")
    return (), frozenset()


def _check(
    *,
    queue: TicketQueue,
    state: FactoryState,
    ledger: SpendLedger,
    caps: Caps,
    config: breakers.BreakerConfig,
    now: datetime,
    frozen_touched: tuple[str, ...] = (),
    canary_ids: frozenset[str] = frozenset(),
) -> list[breakers.BreakerTrip]:
    """Call the module attribute so tests can replace the real checker."""

    return breakers.check_breakers(
        queue=queue,
        state=state,
        ledger=ledger,
        caps=caps,
        config=config,
        now=now,
        frozen_touched=frozen_touched,
        canary_ids=canary_ids,
    )


def _notice_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(line.startswith("factory stopped: ") for line in path.read_text(encoding="utf-8").splitlines())


def _run_one(name: str, subdir: Path, now: datetime) -> DrillResult:
    if subdir.exists():
        shutil.rmtree(subdir)
    subdir.mkdir(parents=True)

    state_path = subdir / "state.json"
    queue = TicketQueue(subdir / "tickets")
    state = FactoryState.load(state_path)
    ledger = SpendLedger(subdir / "ledger.jsonl")
    caps = _caps_for(name)
    config = breakers.BreakerConfig()
    notices_path = subdir / "notices.txt"
    notifier = breakers.FileNotifier(notices_path)

    clean_trips = _check(queue=queue, state=state, ledger=ledger, caps=caps, config=config, now=now)
    frozen_touched, canary_ids = _inject_fault(
        name,
        queue=queue,
        state=state,
        ledger=ledger,
        config=config,
        caps=caps,
        now=now,
    )

    if name == "crash":
        with contextlib.suppress(RuntimeError):
            breakers.guarded_run(
                lambda: (_ for _ in ()).throw(RuntimeError("drill crash")),
                state=state,
                notifier=notifier,
                now_fn=lambda: now,
            )
        trips = [breakers.BreakerTrip("crash", "state machine crashed: RuntimeError: drill crash")]
    else:
        trips = _check(
            queue=queue,
            state=state,
            ledger=ledger,
            caps=caps,
            config=config,
            now=now,
            frozen_touched=frozen_touched,
            canary_ids=canary_ids,
        )
        breakers.trip_all(trips, state=state, notifier=notifier, now=now)

    notice_count_before = _notice_count(notices_path)
    persisted = FactoryState.load(state_path).is_tripped()
    notice_text = notices_path.read_text(encoding="utf-8") if notices_path.exists() else ""
    expected_trip = any(trip.name == name for trip in trips)

    breakers.trip_all(trips, state=state, notifier=notifier, now=now)
    notice_count_after = _notice_count(notices_path)

    failures: list[str] = []
    if clean_trips:
        failures.append("clean control returned trips: " + ", ".join(trip.name for trip in clean_trips))
    if not expected_trip:
        failures.append(f"expected trip {name!r} was not returned")
    if not persisted:
        failures.append("tripped state was not persisted")
    if f"factory stopped: {name}" not in notice_text:
        failures.append("notifier subject did not name the breaker")
    if notice_count_after != notice_count_before:
        failures.append("second trip_all wrote another notice")

    if failures:
        return DrillResult(name, False, "; ".join(failures))
    return DrillResult(
        name, True, f"trip observed, state persisted, and notifier remained idempotent ({notice_count_before} notice)"
    )


def run_drill(workdir: Path, now: datetime) -> list[DrillResult]:
    """Run every breaker drill in its own freshly-created directory."""

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    results: list[DrillResult] = []
    for name in BREAKER_NAMES:
        try:
            results.append(_run_one(name, workdir / name, now))
        except Exception as exc:
            results.append(DrillResult(name, False, f"{type(exc).__name__}: {exc}"))
    return results


def drill_passed(results: list[DrillResult]) -> bool:
    """Return whether every required breaker has a passing result."""

    return all(any(result.name == name and result.passed for result in results) for name in BREAKER_NAMES)


def render_report(results: list[DrillResult]) -> str:
    """Render a compact plain-text report with one row for every breaker."""

    rows = ["breaker | status | detail"]
    passed = 0
    for name in BREAKER_NAMES:
        result = next((item for item in results if item.name == name), None)
        if result is None:
            status = "FAIL"
            detail = "missing result"
        else:
            status = "PASS" if result.passed else "FAIL"
            detail = result.detail
            passed += result.passed
        rows.append(f"{name} | {status} | {detail}")
    rows.append(f"TOTAL: {passed}/{len(BREAKER_NAMES)} PASS")
    return "\n".join(rows)
