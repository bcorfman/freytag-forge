"""Allowlisted model calls and their spend limits."""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from datetime import time as datetime_time
from pathlib import Path
from typing import Any

from factory.limits import LimitReport, Window, window_sleep
from factory.limits import paid_usage as paid_usage_reason


class ModelNotAllowed(Exception):
    """Raised when a station requests a model or effort that is not pinned."""


class BudgetExhausted(Exception):
    """Raised when the factory's total or rate budget is exhausted."""


class LimitSleep(Exception):
    """Raised when a provider lane must sleep until a later time."""

    def __init__(self, provider: str, resume_at: datetime | None) -> None:
        self.provider = provider
        self.resume_at = resume_at
        when = resume_at.isoformat() if resume_at is not None else "an unspecified time"
        super().__init__(f"provider {provider} must sleep until {when}")


class ProviderLimit(Exception):
    """Raised by a provider call when the provider reports its own limit."""

    def __init__(self, resume_at: datetime | None, report: LimitReport | None = None) -> None:
        self.resume_at = resume_at
        self.report = report
        super().__init__("provider reported a limit")


class RateLimited(Exception):
    """Raised when a provider asks for a short retry after a 429 response."""


class Overloaded(Exception):
    """Raised when a provider is temporarily too busy to serve a request."""


@dataclass(frozen=True)
class Pin:
    model_id: str
    effort: str
    provider: str


class ModelGuard:
    """Resolve a station request to one of its explicitly pinned models."""

    def __init__(self, denied_substrings: tuple[str, ...], stations: dict[str, tuple[Pin, ...]]) -> None:
        self.denied_substrings = denied_substrings
        self.stations = stations

    @classmethod
    def from_file(cls, path: str | Path) -> ModelGuard:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        stations = {
            station: tuple(
                Pin(model_id=item["model_id"], effort=item["effort"], provider=item["provider"]) for item in pins
            )
            for station, pins in data["stations"].items()
        }
        denied = tuple(str(value).lower() for value in data.get("denied_substrings", []))
        return cls(denied_substrings=denied, stations=stations)

    def check(self, station: str, model_id: str, effort: str) -> Pin:
        lowered_model_id = model_id.lower()
        if any(substring in lowered_model_id for substring in self.denied_substrings):
            raise ModelNotAllowed(f"model {model_id!r} contains a denied substring")

        pins = self.stations.get(station)
        if pins is None:
            raise ModelNotAllowed(f"unknown station {station!r}")
        for pin in pins:
            if pin.model_id == model_id and pin.effort == effort:
                return pin
        raise ModelNotAllowed(f"model {model_id!r} with effort {effort!r} is not pinned for {station!r}")


@dataclass
class Usage:
    at: datetime
    provider: str
    model_id: str
    station: str
    scene: str
    ticket_id: str
    tokens: int
    usd: float | None
    cost_kind: str = "dollars"
    list_usd: float | None = None
    limits: LimitReport | None = None
    paid_usage: str | None = None

    def __post_init__(self) -> None:
        if self.at.tzinfo is None or self.at.utcoffset() is None:
            raise ValueError("usage timestamp must be timezone-aware")
        if self.cost_kind not in {"dollars", "subscription", "unknown"}:
            raise ValueError(f"unknown usage cost kind: {self.cost_kind!r}")
        if self.cost_kind == "dollars":
            if isinstance(self.usd, bool) or not isinstance(self.usd, (int, float)):
                raise ValueError("dollar usage requires a numeric usd value")
        elif self.usd is not None:
            raise ValueError(f"{self.cost_kind} usage must not have a usd value")


def _limits_payload(report: LimitReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "provider": report.provider,
        "overage": report.overage,
        "credits": report.credits,
        "windows": [
            {
                "name": window.name,
                "used": window.used,
                "resets_at": window.resets_at.isoformat() if window.resets_at is not None else None,
                "rejected": window.rejected,
            }
            for window in report.windows
        ],
    }


def _limits_from_payload(value: Any) -> LimitReport | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("limits must be an object or null")
    raw_windows = value.get("windows", [])
    if not isinstance(raw_windows, list):
        raise ValueError("limits windows must be a list")
    windows = []
    for raw_window in raw_windows:
        if not isinstance(raw_window, dict):
            raise ValueError("limit window must be an object")
        reset = raw_window.get("resets_at")
        if isinstance(reset, str) and reset.endswith("Z"):
            reset = reset[:-1] + "+00:00"
        resets_at = datetime.fromisoformat(reset) if reset is not None else None
        windows.append(
            (
                raw_window["name"],
                float(raw_window["used"]),
                resets_at,
                raw_window["rejected"],
            )
        )
    return LimitReport(
        provider=value["provider"],
        windows=tuple(Window(name, used, resets_at, rejected) for name, used, resets_at, rejected in windows),
        overage=value.get("overage"),
        credits=value.get("credits"),
    )


class SpendLedger:
    """Append-only JSON-lines storage for model usage."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, usage: Usage) -> None:
        payload = {
            "at": usage.at.isoformat(),
            "provider": usage.provider,
            "model_id": usage.model_id,
            "station": usage.station,
            "scene": usage.scene,
            "ticket_id": usage.ticket_id,
            "tokens": usage.tokens,
            "usd": usage.usd,
            "cost_kind": usage.cost_kind,
            "list_usd": usage.list_usd,
            "paid_usage": usage.paid_usage,
            "limits": _limits_payload(usage.limits),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")

    def _read(self) -> list[Usage]:
        if not self.path.exists():
            return []

        usages: list[Usage] = []
        with self.path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    if not line.strip():
                        raise ValueError("blank line")
                    payload = json.loads(line)
                    timestamp = payload["at"]
                    if isinstance(timestamp, str) and timestamp.endswith("Z"):
                        timestamp = timestamp[:-1] + "+00:00"
                    usage = Usage(
                        at=datetime.fromisoformat(timestamp),
                        provider=payload["provider"],
                        model_id=payload["model_id"],
                        station=payload["station"],
                        scene=payload["scene"],
                        ticket_id=payload["ticket_id"],
                        tokens=payload["tokens"],
                        usd=payload.get("usd"),
                        cost_kind=payload.get("cost_kind", "dollars"),
                        list_usd=payload.get("list_usd"),
                        limits=_limits_from_payload(payload.get("limits")),
                        paid_usage=payload.get("paid_usage"),
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"corrupt ledger line {line_number}: {exc}") from exc
                usages.append(usage)
        return usages

    def total_usd(self) -> float:
        return sum(usage.usd for usage in self._read() if usage.cost_kind == "dollars")

    def day_usd(self, provider: str, day: date) -> float:
        return sum(
            usage.usd
            for usage in self._read()
            if usage.cost_kind == "dollars" and usage.provider == provider and _utc_day(usage.at) == day
        )

    def calls(self, model_id: str, day: date, scene: str | None = None) -> int:
        return sum(
            1
            for usage in self._read()
            if usage.model_id == model_id and _utc_day(usage.at) == day and (scene is None or usage.scene == scene)
        )

    def usd_in_window(self, now: datetime, window_s: int) -> float:
        window_start = now - timedelta(seconds=window_s)
        return sum(
            usage.usd for usage in self._read() if usage.cost_kind == "dollars" and window_start <= usage.at <= now
        )

    def unknown_cost_rows(self) -> int:
        return sum(1 for usage in self._read() if usage.cost_kind == "unknown")

    def last_limits(self, provider: str) -> LimitReport | None:
        latest: LimitReport | None = None
        for usage in self._read():
            if usage.provider == provider and usage.limits is not None:
                latest = usage.limits
        return latest

    def paid_usage_reasons(self) -> list[str]:
        return [usage.paid_usage for usage in self._read() if usage.paid_usage is not None]


@dataclass(frozen=True)
class CallCap:
    provider: str
    model_id: str
    per_scene_per_day: int
    per_day: int


@dataclass(frozen=True)
class ProviderPolicy:
    kind: str
    ceilings: dict[str, float]


@dataclass
class Caps:
    total_budget_usd: float
    daily_cap_usd: dict[str, float]
    call_caps: list[CallCap]
    rate_window_s: int
    rate_max_usd: float
    providers: dict[str, ProviderPolicy] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Caps:
        providers: dict[str, ProviderPolicy] = {}
        raw_providers = data.get("providers", {})
        if not isinstance(raw_providers, dict):
            raise ValueError("providers must be an object")
        for provider, raw_policy in raw_providers.items():
            if not isinstance(raw_policy, dict):
                raise ValueError(f"provider policy for {provider!r} must be an object")
            kind = raw_policy.get("kind")
            if kind not in {"subscription", "reported"}:
                raise ValueError(f"unknown provider kind for {provider!r}: {kind!r}")
            raw_ceilings = raw_policy.get("ceilings", {})
            if not isinstance(raw_ceilings, dict):
                raise ValueError(f"ceilings for {provider!r} must be an object")
            ceilings = {name: float(value) for name, value in raw_ceilings.items()}
            if kind == "subscription" and any(value < 0 or value > 1 for value in ceilings.values()):
                raise ValueError(f"subscription ceilings for {provider!r} must be between 0 and 1")
            providers[provider] = ProviderPolicy(kind, ceilings)
        return cls(
            total_budget_usd=float(data["total_budget_usd"]),
            daily_cap_usd={provider: float(cap) for provider, cap in data["daily_cap_usd"].items()},
            call_caps=[
                CallCap(
                    provider=item["provider"],
                    model_id=item["model_id"],
                    per_scene_per_day=int(item["per_scene_per_day"]),
                    per_day=int(item["per_day"]),
                )
                for item in data["call_caps"]
            ],
            rate_window_s=int(data["rate_window_s"]),
            rate_max_usd=float(data["rate_max_usd"]),
            providers=providers,
        )


@dataclass
class CallResult:
    output: Any
    tokens: int
    usd: float | None = None
    limits: LimitReport | None = None


def _utc_day(at: datetime) -> date:
    return at.astimezone(UTC).date()


def _next_midnight_utc(now: datetime) -> datetime:
    utc_now = now.astimezone(UTC)
    tomorrow = utc_now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime_time.min, tzinfo=UTC)


def guarded_call(
    *,
    guard: ModelGuard,
    ledger: SpendLedger,
    caps: Caps,
    station: str,
    model_id: str,
    effort: str,
    scene: str,
    ticket_id: str,
    now: datetime,
    fn: Callable[[], CallResult],
    sleep: Callable[[float], None] = time.sleep,
    rand: Callable[[], float] = random.random,
) -> CallResult:
    pin = guard.check(station, model_id, effort)
    policy = caps.providers.get(pin.provider, ProviderPolicy("reported", {}))

    if policy.kind == "reported":
        if ledger.total_usd() >= caps.total_budget_usd:
            raise BudgetExhausted("total model budget exhausted")

        rate_usd = ledger.usd_in_window(now, caps.rate_window_s)
        if rate_usd > caps.rate_max_usd:
            raise BudgetExhausted(f"rate-of-spend breaker exceeded: {rate_usd} USD in {caps.rate_window_s} seconds")

    utc_day = _utc_day(now)
    if policy.kind == "reported":
        daily_cap = caps.daily_cap_usd.get(pin.provider)
        if daily_cap is not None and ledger.day_usd(pin.provider, utc_day) >= daily_cap:
            raise LimitSleep(pin.provider, _next_midnight_utc(now))
    else:
        report = ledger.last_limits(pin.provider)
        if report is not None:
            decision = window_sleep(report, policy.ceilings)
            if decision.sleep and decision.until is not None and decision.until > now:
                raise LimitSleep(pin.provider, decision.until)

    for call_cap in caps.call_caps:
        if call_cap.provider != pin.provider or call_cap.model_id != pin.model_id:
            continue
        if scene is not None and ledger.calls(pin.model_id, utc_day, scene=scene) >= call_cap.per_scene_per_day:
            raise LimitSleep(pin.provider, _next_midnight_utc(now))
        if ledger.calls(pin.model_id, utc_day) >= call_cap.per_day:
            raise LimitSleep(pin.provider, _next_midnight_utc(now))

    rate_retries = 0
    overload_retries = 0
    overload_delays = (45.0, 90.0, 180.0, 300.0)
    while True:
        try:
            result = fn()
            break
        except RateLimited:
            if rate_retries >= 5:
                raise LimitSleep(pin.provider, None) from None
            sleep(45 + 15 * rand())
            rate_retries += 1
        except Overloaded:
            if overload_retries >= len(overload_delays):
                raise LimitSleep(pin.provider, None) from None
            sleep(overload_delays[overload_retries])
            overload_retries += 1
        except ProviderLimit as exc:
            resume_at = exc.resume_at
            if resume_at is None and exc.report is not None:
                resume_at = window_sleep(exc.report, policy.ceilings).until
            raise LimitSleep(pin.provider, resume_at) from exc

    is_subscription = policy.kind == "subscription"
    usage_cost_kind = "subscription" if is_subscription else ("dollars" if result.usd is not None else "unknown")
    previous_limits = ledger.last_limits(pin.provider) if is_subscription and result.limits is not None else None
    paid_reason = (
        paid_usage_reason(previous_limits, result.limits) if is_subscription and result.limits is not None else None
    )

    ledger.record(
        Usage(
            at=now,
            provider=pin.provider,
            model_id=pin.model_id,
            station=station,
            scene=scene,
            ticket_id=ticket_id,
            tokens=result.tokens,
            usd=None if is_subscription else result.usd,
            cost_kind=usage_cost_kind,
            list_usd=result.usd if is_subscription else None,
            limits=result.limits,
            paid_usage=paid_reason,
        )
    )
    return result
