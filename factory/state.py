"""Durable state for one dark-factory run."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("stored datetime must be timezone-aware")
    return parsed


def _iso_or_string(value: datetime | str) -> str:
    return _utc_iso(value) if isinstance(value, datetime) else value


def _atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            text=True,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary_path)


@dataclass
class FactoryState:
    """The persisted control state shared by factory stations."""

    path: Path
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: str | None = None
    lanes: dict[str, str] = field(default_factory=dict)
    done_keys: list[str] = field(default_factory=list)
    breaker: dict[str, bool | str | None] = field(
        default_factory=lambda: {"tripped": False, "reason": None, "at": None}
    )

    @classmethod
    def load(cls, path: Path) -> FactoryState:
        path = Path(path)
        if not path.exists():
            state = cls(path)
            state.save()
            return state
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        breaker = dict(data.get("breaker", {}))
        breaker.setdefault("tripped", False)
        breaker.setdefault("reason", None)
        breaker.setdefault("at", None)
        return cls(
            path=path,
            run_id=data["run_id"],
            started_at=data.get("started_at"),
            lanes=dict(data.get("lanes", {})),
            done_keys=list(data.get("done_keys", [])),
            breaker=breaker,
        )

    def save(self) -> None:
        _atomic_json_write(
            self.path,
            {
                "run_id": self.run_id,
                "started_at": self.started_at,
                "lanes": self.lanes,
                "done_keys": self.done_keys,
                "breaker": {
                    "tripped": self.breaker.get("tripped", False),
                    "reason": self.breaker.get("reason"),
                    "at": self.breaker.get("at"),
                },
            },
        )

    def sleep_lane(self, provider: str, until: datetime | str) -> None:
        self.lanes[provider] = _iso_or_string(until)
        self.save()

    def lane_ready(self, provider: str, now: datetime) -> bool:
        until = self.lanes.get(provider)
        if until is None:
            return True
        if _parse_datetime(until) <= now:
            del self.lanes[provider]
            self.save()
            return True
        return False

    def sleeping_lanes(self, now: datetime) -> dict[str, str]:
        expired = [provider for provider, until in self.lanes.items() if _parse_datetime(until) <= now]
        for provider in expired:
            del self.lanes[provider]
        if expired:
            self.save()
        return dict(self.lanes)

    def mark_once(self, key: str) -> bool:
        if key in self.done_keys:
            self.save()
            return False
        self.done_keys.append(key)
        self.save()
        return True

    def trip_breaker(self, reason: str, now: datetime) -> None:
        self.breaker = {"tripped": True, "reason": reason, "at": _utc_iso(now)}
        self.save()

    def is_tripped(self) -> bool:
        return bool(self.breaker.get("tripped", False))

    def breaker_reason(self) -> str | None:
        reason = self.breaker.get("reason")
        return reason if isinstance(reason, str) else None
