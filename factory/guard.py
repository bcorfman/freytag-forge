"""Allowlisted model calls and their spend limits."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any


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

    def __init__(self, resume_at: datetime | None) -> None:
        self.resume_at = resume_at
        super().__init__("provider reported a limit")


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
    usd: float

    def __post_init__(self) -> None:
        if self.at.tzinfo is None or self.at.utcoffset() is None:
            raise ValueError("usage timestamp must be timezone-aware")


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
                        usd=payload["usd"],
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"corrupt ledger line {line_number}: {exc}") from exc
                usages.append(usage)
        return usages

    def total_usd(self) -> float:
        return sum(usage.usd for usage in self._read())

    def day_usd(self, provider: str, day: date) -> float:
        return sum(usage.usd for usage in self._read() if usage.provider == provider and _utc_day(usage.at) == day)

    def calls(self, model_id: str, day: date, scene: str | None = None) -> int:
        return sum(
            1
            for usage in self._read()
            if usage.model_id == model_id and _utc_day(usage.at) == day and (scene is None or usage.scene == scene)
        )

    def usd_in_window(self, now: datetime, window_s: int) -> float:
        window_start = now - timedelta(seconds=window_s)
        return sum(usage.usd for usage in self._read() if window_start <= usage.at <= now)


@dataclass(frozen=True)
class CallCap:
    provider: str
    model_id: str
    per_scene_per_day: int
    per_day: int


@dataclass
class Caps:
    total_budget_usd: float
    daily_cap_usd: dict[str, float]
    call_caps: list[CallCap]
    rate_window_s: int
    rate_max_usd: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Caps:
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
        )


@dataclass
class CallResult:
    output: Any
    tokens: int
    usd: float


def _utc_day(at: datetime) -> date:
    return at.astimezone(UTC).date()


def _next_midnight_utc(now: datetime) -> datetime:
    utc_now = now.astimezone(UTC)
    tomorrow = utc_now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=UTC)


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
) -> CallResult:
    pin = guard.check(station, model_id, effort)

    if ledger.total_usd() >= caps.total_budget_usd:
        raise BudgetExhausted("total model budget exhausted")

    rate_usd = ledger.usd_in_window(now, caps.rate_window_s)
    if rate_usd > caps.rate_max_usd:
        raise BudgetExhausted(f"rate-of-spend breaker exceeded: {rate_usd} USD in {caps.rate_window_s} seconds")

    utc_day = _utc_day(now)
    daily_cap = caps.daily_cap_usd.get(pin.provider)
    if daily_cap is not None and ledger.day_usd(pin.provider, utc_day) >= daily_cap:
        raise LimitSleep(pin.provider, _next_midnight_utc(now))

    for call_cap in caps.call_caps:
        if call_cap.provider != pin.provider or call_cap.model_id != pin.model_id:
            continue
        if scene is not None and ledger.calls(pin.model_id, utc_day, scene=scene) >= call_cap.per_scene_per_day:
            raise LimitSleep(pin.provider, _next_midnight_utc(now))
        if ledger.calls(pin.model_id, utc_day) >= call_cap.per_day:
            raise LimitSleep(pin.provider, _next_midnight_utc(now))

    try:
        result = fn()
    except ProviderLimit as exc:
        raise LimitSleep(pin.provider, exc.resume_at) from exc

    ledger.record(
        Usage(
            at=now,
            provider=pin.provider,
            model_id=pin.model_id,
            station=station,
            scene=scene,
            ticket_id=ticket_id,
            tokens=result.tokens,
            usd=result.usd,
        )
    )
    return result
