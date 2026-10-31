"""Run one bounded request with at most one delayed duplicate."""

from __future__ import annotations

import queue
from collections.abc import Callable
from dataclasses import dataclass
from os import getenv
from threading import Thread
from time import monotonic
from typing import Literal

Attempt = Literal["primary", "hedge"]
Clock = Callable[[], float]
ThreadStarter = Callable[[Callable[[], None]], None]


@dataclass(frozen=True)
class HedgedResult[T]:
    """The winning value and the request-attempt telemetry for one call."""

    value: T
    hedge_fired: bool
    winner: Attempt


@dataclass(frozen=True)
class _AttemptResult[T]:
    attempt: Attempt
    value: T | None = None
    error: BaseException | None = None


def _start_daemon_thread(target: Callable[[], None]) -> None:
    Thread(target=target, daemon=True).start()


def configured_hedge_delay(default: float) -> float:
    """Return the configured delay, with zero disabling hedging."""

    configured = getenv("FREYTAG_HEDGE_DELAY_S")
    if configured is None:
        return default
    try:
        return max(0.0, float(configured))
    except ValueError:
        return default


class HedgedRequester:
    """Coordinate a primary request and one optional duplicate."""

    def __init__(
        self,
        *,
        clock: Clock = monotonic,
        thread_starter: ThreadStarter = _start_daemon_thread,
    ) -> None:
        self._clock = clock
        self._thread_starter = thread_starter

    def call[T](self, send: Callable[[], T], *, delay_s: float, timeout_s: float | None) -> HedgedResult[T]:
        if delay_s < 0:
            raise ValueError("delay_s must be non-negative")
        if timeout_s is not None and timeout_s <= 0:
            raise ValueError("timeout_s must be positive")

        results: queue.Queue[_AttemptResult[T]] = queue.Queue()
        started = self._clock()
        deadline = started + timeout_s if timeout_s is not None else None

        def run(attempt: Attempt) -> None:
            try:
                results.put(_AttemptResult(attempt, value=send()))
            except BaseException as error:
                results.put(_AttemptResult(attempt, error=error))

        self._thread_starter(lambda: run("primary"))
        if delay_s == 0:
            outcome = self._get_until(results, deadline)
            if outcome is None:
                raise TimeoutError("hedged request timed out")
            if outcome.error is not None:
                raise outcome.error
            return HedgedResult(outcome.value, False, "primary")  # type: ignore[arg-type]

        first_deadline = started + delay_s if deadline is None else min(started + delay_s, deadline)
        first = self._get_until(results, first_deadline)
        if first is not None:
            if first.error is not None:
                raise first.error
            return HedgedResult(first.value, False, first.attempt)  # type: ignore[arg-type]

        if deadline is not None and self._clock() >= deadline:
            raise TimeoutError("hedged request timed out")

        self._thread_starter(lambda: run("hedge"))
        first_failure: BaseException | None = None
        failures = 0
        while True:
            outcome = self._get_until(results, deadline)
            if outcome is None:
                if first_failure is not None:
                    raise first_failure
                raise TimeoutError("hedged request timed out")
            if outcome.error is None:
                return HedgedResult(outcome.value, True, outcome.attempt)  # type: ignore[arg-type]
            if first_failure is None:
                first_failure = outcome.error
            failures += 1
            if failures == 2:
                raise first_failure

    def _get_until[T](
        self,
        results: queue.Queue[_AttemptResult[T]],
        deadline: float | None,
    ) -> _AttemptResult[T] | None:
        while True:
            if deadline is None:
                return results.get()
            remaining = deadline - self._clock()
            if remaining <= 0:
                return None
            try:
                return results.get(timeout=remaining)
            except queue.Empty:
                if self._clock() >= deadline:
                    return None


def hedged_call[T](
    send: Callable[[], T],
    *,
    delay_s: float,
    timeout_s: float | None,
    clock: Clock = monotonic,
    thread_starter: ThreadStarter = _start_daemon_thread,
) -> HedgedResult[T]:
    """Run ``send`` with one delayed duplicate and a shared total deadline."""

    return HedgedRequester(clock=clock, thread_starter=thread_starter).call(
        send,
        delay_s=delay_s,
        timeout_s=timeout_s,
    )
