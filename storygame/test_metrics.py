"""Low-overhead runtime counters used by the test-suite health report."""

from __future__ import annotations

from collections import Counter
from contextvars import ContextVar
from typing import Any

_active: ContextVar[Counter[str] | None] = ContextVar("test_metrics", default=None)
_total: Counter[str] = Counter()


def begin_test() -> None:
    _active.set(Counter())


def end_test() -> dict[str, int]:
    bucket = _active.get() or Counter()
    _active.set(None)
    return dict(bucket)


def record(operation: str, **details: Any) -> None:
    _total[operation] += 1
    bucket = _active.get()
    if bucket is None:
        return
    bucket[operation] += 1
    for key, value in details.items():
        if value is not None:
            bucket[f"{operation}.{key}.{value}"] += 1


def totals() -> dict[str, int]:
    return dict(_total)


def reset_totals() -> None:
    _total.clear()
