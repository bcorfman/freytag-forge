"""Allowlisted model calls and their spend limits."""

from __future__ import annotations

import json
import math
import os
import random
import time
import uuid
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
    estimate_usd: float | None = None
    reservation_id: str | None = None

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
        if self.estimate_usd is not None and (
            isinstance(self.estimate_usd, bool) or not isinstance(self.estimate_usd, (int, float))
        ):
            raise ValueError("estimate_usd must be a number or null")
        if self.estimate_usd is not None and self.estimate_usd < 0:
            raise ValueError("estimate_usd must not be negative")


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

    def _append(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _events(self) -> tuple[list[Usage], list[dict[str, Any]]]:
        usages: list[Usage] = []
        events: list[dict[str, Any]] = []
        if not self.path.exists():
            return usages, events
        with self.path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    if not line.strip():
                        raise ValueError("blank line")
                    payload = json.loads(line)
                    if not isinstance(payload, dict):
                        raise ValueError("ledger row must be an object")
                    kind = payload.get("kind")
                    if kind in {"reservation", "release"}:
                        if kind == "reservation":
                            timestamp = payload["at"]
                            if isinstance(timestamp, str) and timestamp.endswith("Z"):
                                timestamp = timestamp[:-1] + "+00:00"
                            at = datetime.fromisoformat(timestamp)
                            usd = payload["usd"]
                            if at.tzinfo is None or at.utcoffset() is None:
                                raise ValueError("reservation timestamp must be timezone-aware")
                            if (
                                isinstance(usd, bool)
                                or not isinstance(usd, (int, float))
                                or not math.isfinite(usd)
                                or usd < 0
                            ):
                                raise ValueError("reservation usd must be a finite non-negative number")
                            for key in ("reservation_id", "provider", "model_id", "station", "scene", "ticket_id"):
                                if not isinstance(payload[key], str) or not payload[key]:
                                    raise ValueError(f"reservation {key} must be a non-empty string")
                        else:
                            if not isinstance(payload["reservation_id"], str) or not payload["reservation_id"]:
                                raise ValueError("release reservation_id must be a non-empty string")
                            timestamp = payload["at"]
                            if isinstance(timestamp, str) and timestamp.endswith("Z"):
                                timestamp = timestamp[:-1] + "+00:00"
                            release_at = datetime.fromisoformat(timestamp)
                            if release_at.tzinfo is None or release_at.utcoffset() is None:
                                raise ValueError("release timestamp must be timezone-aware")
                        events.append(payload)
                        continue
                    usage = Usage(
                        at=datetime.fromisoformat(payload["at"].replace("Z", "+00:00")),
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
                        estimate_usd=payload.get("estimate_usd"),
                        reservation_id=payload.get("reservation_id"),
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"corrupt ledger line {line_number}: {exc}") from exc
                usages.append(usage)
        return usages, events

    def record(self, usage: Usage, reservation_id: str | None = None) -> None:
        reservation_id = reservation_id if reservation_id is not None else usage.reservation_id
        if reservation_id is not None:
            _, events = self._events()
            reservations = {event["reservation_id"] for event in events if event["kind"] == "reservation"}
            settled = {event["reservation_id"] for event in events if event["kind"] == "release"}
            settled.update(usage.reservation_id for usage in self._read() if usage.reservation_id is not None)
            if reservation_id not in reservations or reservation_id in settled:
                raise ValueError(f"unknown or settled reservation id: {reservation_id}")
        payload = {
            "at": usage.at.isoformat(),
            "provider": usage.provider,
            "model_id": usage.model_id,
            "station": usage.station,
            "scene": usage.scene,
            "ticket_id": usage.ticket_id,
            "tokens": usage.tokens,
            "usd": usage.usd,
            "estimate_usd": usage.estimate_usd,
            "cost_kind": usage.cost_kind,
            "list_usd": usage.list_usd,
            "paid_usage": usage.paid_usage,
            "limits": _limits_payload(usage.limits),
        }
        if reservation_id is not None:
            payload["reservation_id"] = reservation_id
        self._append(payload)

    def reserve(
        self,
        *,
        provider: str,
        model_id: str,
        station: str,
        scene: str,
        ticket_id: str,
        usd: float,
        now: datetime,
        caps: Caps | None = None,
    ) -> str:
        if isinstance(usd, bool) or not isinstance(usd, (int, float)) or not math.isfinite(usd) or usd < 0:
            raise ValueError("reservation usd must be a finite non-negative number")
        if caps is not None:
            if self.total_usd() + usd > caps.total_budget_usd:
                raise BudgetExhausted("total model budget exhausted")
            if self.day_usd(provider, _utc_day(now)) + usd > caps.daily_cap_usd.get(provider, math.inf):
                raise BudgetExhausted("daily model budget exhausted")
        reservation_id = uuid.uuid4().hex
        self._append(
            {
                "kind": "reservation",
                "reservation_id": reservation_id,
                "at": now.isoformat(),
                "provider": provider,
                "model_id": model_id,
                "station": station,
                "scene": scene,
                "ticket_id": ticket_id,
                "usd": usd,
            }
        )
        return reservation_id

    def release(self, reservation_id: str) -> None:
        _, events = self._events()
        reservations = {event["reservation_id"] for event in events if event["kind"] == "reservation"}
        settled = {event["reservation_id"] for event in events if event["kind"] == "release"}
        settled.update(usage.reservation_id for usage in self._read() if usage.reservation_id is not None)
        if reservation_id not in reservations or reservation_id in settled:
            raise ValueError(f"unknown or settled reservation id: {reservation_id}")
        self._append({"kind": "release", "reservation_id": reservation_id, "at": datetime.now(UTC).isoformat()})

    def open_reservations(self) -> list[dict[str, Any]]:
        usages, events = self._events()
        settled = {event["reservation_id"] for event in events if event["kind"] == "release"}
        settled.update(usage.reservation_id for usage in usages if usage.reservation_id is not None)
        return [event for event in events if event["kind"] == "reservation" and event["reservation_id"] not in settled]

    def _read(self) -> list[Usage]:
        return self._events()[0]

    def total_usd(self) -> float:
        return sum(usage.usd for usage in self._read() if usage.cost_kind == "dollars") + sum(
            event["usd"] for event in self.open_reservations()
        )

    def day_usd(self, provider: str, day: date) -> float:
        return sum(
            usage.usd
            for usage in self._read()
            if usage.cost_kind == "dollars" and usage.provider == provider and _utc_day(usage.at) == day
        ) + sum(
            event["usd"]
            for event in self.open_reservations()
            if event["provider"] == provider and _utc_day(_event_time(event)) == day
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
        ) + sum(event["usd"] for event in self.open_reservations() if window_start <= _event_time(event) <= now)

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

    def estimate_report(self) -> list[dict]:
        grouped: dict[str, dict[str, float | int]] = {}
        for usage in self._read():
            if usage.cost_kind != "dollars":
                continue
            if (
                isinstance(usage.estimate_usd, bool)
                or not isinstance(usage.estimate_usd, (int, float))
                or isinstance(usage.usd, bool)
                or not isinstance(usage.usd, (int, float))
            ):
                continue
            entry = grouped.setdefault(usage.station, {"calls": 0, "estimate_usd": 0.0, "actual_usd": 0.0})
            entry["calls"] += 1
            entry["estimate_usd"] += usage.estimate_usd
            entry["actual_usd"] += usage.usd

        report = []
        for station in sorted(grouped):
            entry = grouped[station]
            estimate_usd = entry["estimate_usd"]
            actual_usd = entry["actual_usd"]
            report.append(
                {
                    "station": station,
                    "calls": entry["calls"],
                    "estimate_usd": estimate_usd,
                    "actual_usd": actual_usd,
                    "ratio": round(actual_usd / estimate_usd, 2) if estimate_usd else None,
                }
            )
        return report


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


def _event_time(event: dict[str, Any]) -> datetime:
    timestamp = event["at"]
    if timestamp.endswith("Z"):
        timestamp = timestamp[:-1] + "+00:00"
    return datetime.fromisoformat(timestamp)


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
    estimate_usd: float | None = None,
) -> CallResult:
    pin = guard.check(station, model_id, effort)
    policy = caps.providers.get(pin.provider, ProviderPolicy("reported", {}))

    if policy.kind == "reported":
        if estimate_usd is None:
            raise BudgetExhausted("a dollar-priced call needs an estimate_usd to reserve")
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
        reservation_id = None
        if policy.kind == "reported":
            reservation_id = ledger.reserve(
                provider=pin.provider,
                model_id=pin.model_id,
                station=station,
                scene=scene,
                ticket_id=ticket_id,
                usd=estimate_usd,
                now=now,
                caps=caps,
            )
        try:
            result = fn()
            break
        except RateLimited:
            if reservation_id is not None:
                ledger.release(reservation_id)
            if rate_retries >= 5:
                raise LimitSleep(pin.provider, None) from None
            sleep(45 + 15 * rand())
            rate_retries += 1
        except Overloaded:
            if reservation_id is not None:
                ledger.release(reservation_id)
            if overload_retries >= len(overload_delays):
                raise LimitSleep(pin.provider, None) from None
            sleep(overload_delays[overload_retries])
            overload_retries += 1
        except ProviderLimit as exc:
            if reservation_id is not None:
                ledger.release(reservation_id)
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
            estimate_usd=estimate_usd,
        ),
        reservation_id=reservation_id,
    )
    return result
