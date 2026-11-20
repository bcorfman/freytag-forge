"""Pure readers and decisions for subscription-provider rate limits."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Window:
    """A provider rate-limit window."""

    name: str
    used: float
    resets_at: datetime | None
    rejected: bool


@dataclass(frozen=True)
class LimitReport:
    """The latest rate-limit information reported by one provider."""

    provider: str
    windows: tuple[Window, ...]
    overage: bool | None
    credits: float | None


def _reset_time(value: Any) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def read_claude_stream(lines: Iterable[str], provider: str = "claude_code") -> LimitReport | None:
    """Read the last Claude rate-limit event from a stream of JSON lines."""

    event: dict[str, Any] | None = None
    for line in lines:
        try:
            value = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict) and value.get("type") == "rate_limit_event":
            event = value
    if event is None:
        return None

    info = event.get("rate_limit_info")
    if not isinstance(info, dict):
        return LimitReport(provider, (), None, None)
    windows_value = info.get("unifiedWindows", {})
    windows: list[Window] = []
    if isinstance(windows_value, dict):
        for name, raw_window in windows_value.items():
            if not isinstance(name, str) or not isinstance(raw_window, dict):
                continue
            used = _number(raw_window.get("utilization"))
            if used is None:
                continue
            windows.append(
                Window(
                    name=name,
                    used=used,
                    resets_at=_reset_time(raw_window.get("resetsAt")),
                    rejected=raw_window.get("status") == "rejected",
                )
            )
    windows.sort(key=lambda window: window.name)
    return LimitReport(provider, tuple(windows), info.get("isUsingOverage"), None)


def find_codex_session(thread_id: str, sessions_root: Path) -> Path | None:
    """Find the most recently modified Codex session for a thread."""

    matches = [path for path in sessions_root.rglob("*.jsonl") if path.name.endswith(f"-{thread_id}.jsonl")]
    return max(matches, key=lambda path: path.stat().st_mtime, default=None)


def read_codex_session(path: Path, provider: str = "codex") -> LimitReport | None:
    """Read the last Codex rate-limit record from a session JSONL file."""

    rate_limits: dict[str, Any] | None = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            payload = value.get("payload") if isinstance(value, dict) else None
            candidate = payload.get("rate_limits") if isinstance(payload, dict) else None
            if isinstance(candidate, dict):
                rate_limits = candidate
    if rate_limits is None:
        return None

    windows: list[Window] = []
    for key, name in (("primary", "five_hour"), ("secondary", "seven_day")):
        raw_window = rate_limits.get(key)
        if not isinstance(raw_window, dict):
            continue
        used_percent = _number(raw_window.get("used_percent"))
        if used_percent is None:
            continue
        used = used_percent / 100
        windows.append(
            Window(
                name=name,
                used=used,
                resets_at=_reset_time(raw_window.get("resets_at")),
                rejected=used >= 1.0,
            )
        )

    credits_value = rate_limits.get("credits")
    balance = credits_value.get("balance") if isinstance(credits_value, dict) else None
    try:
        credits = float(balance) if balance is not None else None
    except (TypeError, ValueError):
        credits = None
    return LimitReport(provider, tuple(sorted(windows, key=lambda window: window.name)), None, credits)


@dataclass(frozen=True)
class SleepDecision:
    """Whether a provider lane must wait for one or more windows."""

    sleep: bool
    until: datetime | None
    reason: str


def _percentage(value: float) -> str:
    return f"{value * 100:g}%"


def _reset_text(value: datetime | None) -> str:
    return value.isoformat() if value is not None else "unknown"


def window_sleep(report: LimitReport, ceilings: dict[str, float]) -> SleepDecision:
    """Decide whether hit windows require sleeping until their latest reset."""

    hits: list[tuple[Window, float | None]] = []
    for window in report.windows:
        ceiling = ceilings.get(window.name)
        if window.rejected or (ceiling is not None and window.used >= ceiling):
            hits.append((window, ceiling))
    if not hits:
        return SleepDecision(False, None, "")

    reasons = []
    for window, ceiling in hits:
        if window.rejected:
            reasons.append(f"{window.name} {_percentage(window.used)} rejected, resets {_reset_text(window.resets_at)}")
        else:
            reasons.append(
                f"{window.name} {_percentage(window.used)} >= ceiling {_percentage(ceiling or 0)}, "
                f"resets {_reset_text(window.resets_at)}"
            )
    reset_times = [window.resets_at for window, _ in hits]
    until = (
        None
        if any(reset is None for reset in reset_times)
        else max(reset for reset in reset_times if reset is not None)
    )
    return SleepDecision(True, until, "; ".join(reasons))


def paid_usage(before: LimitReport | None, after: LimitReport) -> str | None:
    """Return a reason if a report indicates paid overage or reduced credits."""

    if after.overage is True:
        return f"{after.provider} reports paid overage in use"
    if (
        before is not None
        and before.credits is not None
        and after.credits is not None
        and after.credits < before.credits
    ):
        return f"{after.provider} credits dropped from {before.credits} to {after.credits}"
    return None
