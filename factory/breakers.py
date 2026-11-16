"""Circuit breakers and owner notifications for the dark factory."""

from __future__ import annotations

import statistics
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from factory.guard import Caps, SpendLedger
from factory.state import FactoryState
from factory.tickets import Status, Ticket, TicketQueue, repeat_failure_count


@dataclass(frozen=True)
class BreakerTrip:
    """Evidence that one factory circuit breaker has fired."""

    name: str
    reason: str


@dataclass
class BreakerConfig:
    """Thresholds used by the factory circuit breakers."""

    repeat_failures: int = 3
    token_median_factor: float = 5.0
    min_tickets_for_median: int = 5
    provider_overdue_s: int = 86400


class Notifier(Protocol):
    """Deliver one owner notification."""

    def notify(self, subject: str, body: str) -> None:
        """Notify the owner with a subject and body."""


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored datetime must be timezone-aware")
    return parsed


def _ticket_is_sleeping(ticket: Ticket) -> bool:
    return ticket.status is Status.SLEEPING


def _ticket_breaker_trips(
    queue: TicketQueue, config: BreakerConfig, canary_ids: frozenset[str]
) -> tuple[BreakerTrip | None, BreakerTrip | None, BreakerTrip | None]:
    tickets = [ticket for ticket in queue.all() if not _ticket_is_sleeping(ticket)]
    repeat_trip: BreakerTrip | None = None
    token_trip: BreakerTrip | None = None
    canary_trip: BreakerTrip | None = None

    repeat_ticket = next(
        (ticket for ticket in tickets if repeat_failure_count(ticket) >= config.repeat_failures),
        None,
    )
    if repeat_ticket is not None:
        failure = repeat_ticket.failures[-1]
        count = repeat_failure_count(repeat_ticket)
        repeat_trip = BreakerTrip(
            "repeat_failure",
            f"ticket {repeat_ticket.id} has {count} consecutive failures for check "
            f"{failure.check!r} and output hash {failure.output_hash!r}.",
        )

    token_values = [ticket.tokens_used for ticket in tickets if ticket.tokens_used > 0]
    if len(token_values) >= config.min_tickets_for_median:
        median = statistics.median(token_values)
        outlier = next(
            (ticket for ticket in tickets if ticket.tokens_used > config.token_median_factor * median),
            None,
        )
        if outlier is not None:
            token_trip = BreakerTrip(
                "token_outlier",
                f"ticket {outlier.id} used {outlier.tokens_used} tokens, above "
                f"{config.token_median_factor} times the median of {median} tokens.",
            )

    canary_ticket = next(
        (ticket for ticket in tickets if ticket.id in canary_ids and ticket.status is Status.PASSED),
        None,
    )
    if canary_ticket is not None:
        canary_trip = BreakerTrip(
            "canary_passed",
            f"canary ticket {canary_ticket.id} unexpectedly passed.",
        )
    return repeat_trip, token_trip, canary_trip


def check_breakers(
    *,
    queue: TicketQueue,
    state: FactoryState,
    ledger: SpendLedger,
    caps: Caps,
    config: BreakerConfig,
    now: datetime,
    frozen_touched: tuple[str, ...] = (),
    canary_ids: frozenset[str] = frozenset(),
    delivered: bool = False,
) -> list[BreakerTrip]:
    """Return all breaker trips, in the factory's fixed evaluation order."""

    trips: list[BreakerTrip] = []
    total_usd = ledger.total_usd()
    if total_usd >= caps.total_budget_usd and not delivered:
        trips.append(
            BreakerTrip(
                "budget_spent",
                f"total spend {total_usd:.6f} USD reached the budget cap of {caps.total_budget_usd:.6f} USD.",
            )
        )

    rate_usd = ledger.usd_in_window(now, caps.rate_window_s)
    if rate_usd > caps.rate_max_usd:
        trips.append(
            BreakerTrip(
                "spend_rate",
                f"spend rate {rate_usd:.6f} USD exceeded the cap of {caps.rate_max_usd:.6f} USD "
                f"in {caps.rate_window_s} seconds.",
            )
        )

    repeat_trip, token_trip, canary_trip = _ticket_breaker_trips(queue, config, canary_ids)
    if repeat_trip is not None:
        trips.append(repeat_trip)
    if token_trip is not None:
        trips.append(token_trip)

    overdue_provider = next(
        (
            provider
            for provider, sleep_until in state.lanes.items()
            if _parse_datetime(sleep_until) + timedelta(seconds=config.provider_overdue_s) <= now
        ),
        None,
    )
    if overdue_provider is not None:
        trips.append(
            BreakerTrip(
                "provider_overdue",
                f"provider {overdue_provider} remained unavailable past its overdue deadline.",
            )
        )

    if canary_trip is not None:
        trips.append(canary_trip)

    if frozen_touched:
        paths = ", ".join(str(path) for path in frozen_touched[:5])
        trips.append(BreakerTrip("harness_changed", f"frozen harness paths were changed: {paths}."))

    return trips


class FileNotifier:
    """Append owner notifications to a plain text file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def notify(self, subject: str, body: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{subject}\n{body}\n\n")


class CommandNotifier:
    """Send owner notifications to a command without invoking a shell."""

    def __init__(self, argv: list[str]) -> None:
        self.argv = list(argv)
        self.last_error: BaseException | None = None

    def notify(self, subject: str, body: str) -> None:
        self.last_error = None
        command = self.argv + [subject, body]
        try:
            result = subprocess.run(command, check=False, shell=False, timeout=30)
        except Exception as exc:
            self.last_error = exc
            return
        if result.returncode != 0:
            self.last_error = subprocess.CalledProcessError(result.returncode, command)


def trip_all(trips: list[BreakerTrip], *, state: FactoryState, notifier: Notifier, now: datetime) -> bool:
    """Persist and notify the first breaker transition."""

    if not trips:
        return False
    if state.is_tripped():
        return True

    state.trip_breaker("; ".join(trip.reason for trip in trips), now)
    state.save()
    names = ", ".join(trip.name for trip in trips)
    body = "\n".join(trip.reason for trip in trips)
    notifier.notify(f"factory stopped: {names}", body)
    return True


def guarded_run(
    fn: Callable[[], Any], *, state: FactoryState, notifier: Notifier, now_fn: Callable[[], datetime]
) -> Any:
    """Run the state machine, tripping the crash breaker before re-raising failures."""

    try:
        return fn()
    except Exception as exc:
        trip_all(
            [BreakerTrip("crash", f"state machine crashed: {type(exc).__name__}: {exc}")],
            state=state,
            notifier=notifier,
            now=now_fn(),
        )
        raise
