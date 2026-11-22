"""Ticket definitions and the durable on-disk ticket queue."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any


class TicketClass(StrEnum):
    """The kind of work a ticket describes."""

    STORY_DATA = "story_data"
    WORLD_MODEL = "world_model"
    NARRATOR_PROMPT = "narrator_prompt"
    ENGINE = "engine"


class Status(StrEnum):
    """The lifecycle state of a ticket."""

    QUEUED = "queued"
    RUNNING = "running"
    SLEEPING = "sleeping"
    PASSED = "passed"
    FAILED = "failed"
    SET_ASIDE = "set_aside"


class Station(IntEnum):
    """The fixed station sequence in the factory."""

    ACT_CONTRACTS = 0
    CONTRACT_REFRESH = 1
    WORLD_NEED = 2
    PROSE = 3
    WIRING = 4
    FREE_GATES = 5
    PROMPT_SNAPSHOT = 6
    LIVE_PLAYTEST = 7
    TRIAGE = 8
    DELIVER = 9
    FUN_REVIEW = 10
    DIAGNOSE = 11


class LadderRung(IntEnum):
    """The provider escalation rung for a ticket."""

    LUNA_RETRY = 1
    SONNET_REWRITE = 2
    OPUS_REFRESH = 3
    SET_ASIDE = 4


@dataclass
class Failure:
    """A compact record of one failed check."""

    check: str
    output_hash: str
    at: str


def output_hash(text: str) -> str:
    """Return the short stable hash used in failure records."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class Ticket:
    """A unit of factory work and its persisted execution history."""

    id: str
    scene: str
    station: Station
    token_budget: int
    created_at: str
    updated_at: str
    status: Status = Status.QUEUED
    ticket_class: TicketClass | None = None
    ladder_rung: LadderRung = LadderRung.LUNA_RETRY
    attempts: int = 0
    tokens_used: int = 0
    failures: list[Failure] = field(default_factory=list)
    provider: str | None = None
    sleep_until: str | None = None
    return_after: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of this ticket."""

        return {
            "id": self.id,
            "scene": self.scene,
            "station": self.station.value,
            "status": self.status.value,
            "ticket_class": self.ticket_class.value if self.ticket_class is not None else None,
            "ladder_rung": self.ladder_rung.value,
            "attempts": self.attempts,
            "token_budget": self.token_budget,
            "tokens_used": self.tokens_used,
            "failures": [
                {"check": failure.check, "output_hash": failure.output_hash, "at": failure.at}
                for failure in self.failures
            ],
            "provider": self.provider,
            "sleep_until": self.sleep_until,
            "return_after": self.return_after,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ticket:
        """Build a ticket from its JSON representation."""

        ticket_class = data.get("ticket_class")
        return cls(
            id=data["id"],
            scene=data["scene"],
            station=Station(data["station"]),
            token_budget=data["token_budget"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            status=Status(data.get("status", Status.QUEUED.value)),
            ticket_class=TicketClass(ticket_class) if ticket_class is not None else None,
            ladder_rung=LadderRung(data.get("ladder_rung", LadderRung.LUNA_RETRY.value)),
            attempts=data.get("attempts", 0),
            tokens_used=data.get("tokens_used", 0),
            failures=[Failure(**failure) for failure in data.get("failures", [])],
            provider=data.get("provider"),
            sleep_until=data.get("sleep_until"),
            return_after=data.get("return_after"),
            payload=data.get("payload", {}),
        )


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


def repeat_failure_count(ticket: Ticket) -> int:
    """Count the consecutive occurrences of the final failure signature."""

    if not ticket.failures:
        return 0
    last = ticket.failures[-1]
    count = 0
    for failure in reversed(ticket.failures):
        if failure.check != last.check or failure.output_hash != last.output_hash:
            break
        count += 1
    return count


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


class TicketQueue:
    """A directory-backed queue with one atomically written file per ticket."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, ticket_id: str) -> Path:
        return self.root / f"{ticket_id}.json"

    def add(self, ticket: Ticket) -> None:
        path = self._path(ticket.id)
        if path.exists():
            raise ValueError(f"ticket already exists: {ticket.id}")
        _atomic_json_write(path, ticket.to_dict())

    def get(self, ticket_id: str) -> Ticket:
        path = self._path(ticket_id)
        if not path.exists():
            raise KeyError(ticket_id)
        with path.open(encoding="utf-8") as handle:
            return Ticket.from_dict(json.load(handle))

    def save(self, ticket: Ticket) -> None:
        _atomic_json_write(self._path(ticket.id), ticket.to_dict())

    def all(self) -> list[Ticket]:
        tickets = []
        for path in self.root.glob("*.json"):
            with path.open(encoding="utf-8") as handle:
                tickets.append(Ticket.from_dict(json.load(handle)))
        return sorted(tickets, key=lambda ticket: (ticket.created_at, ticket.id))

    def by_status(self, status: Status) -> list[Ticket]:
        return [ticket for ticket in self.all() if ticket.status == status]

    def next_ready(self, now: datetime) -> Ticket | None:
        ready = []
        for ticket in self.all():
            if ticket.status is Status.QUEUED:
                ready.append(ticket)
            elif ticket.status is Status.SLEEPING and ticket.sleep_until is not None:
                if _parse_datetime(ticket.sleep_until) <= now:
                    ready.append(ticket)
            elif (
                ticket.status is Status.SET_ASIDE
                and ticket.return_after is not None
                and _parse_datetime(ticket.return_after) <= now
            ):
                ready.append(ticket)
        return ready[0] if ready else None

    def record_failure(
        self,
        ticket_id: str,
        check: str,
        output: str,
        now: datetime,
        max_attempts: int = 3,
        set_aside_s: int = 21600,
    ) -> Ticket:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        ticket = self.get(ticket_id)
        ticket.failures.append(Failure(check, output_hash(output), _utc_iso(now)))
        ticket.attempts += 1
        ticket.updated_at = _utc_iso(now)

        if ticket.ladder_rung is LadderRung.SET_ASIDE:
            ticket.status = Status.SET_ASIDE
            ticket.return_after = _utc_iso(now + timedelta(seconds=set_aside_s))
        elif ticket.attempts >= max_attempts:
            ticket.attempts = 0
            if ticket.ladder_rung is LadderRung.OPUS_REFRESH:
                ticket.ladder_rung = LadderRung.SET_ASIDE
                ticket.status = Status.SET_ASIDE
                ticket.return_after = _utc_iso(now + timedelta(seconds=set_aside_s))
            else:
                ticket.ladder_rung = LadderRung(ticket.ladder_rung + 1)
                ticket.status = Status.QUEUED
        else:
            ticket.status = Status.QUEUED
        self.save(ticket)
        return ticket

    def record_limit_hit(self, ticket_id: str, provider: str, resume_at: datetime | str, now: datetime) -> Ticket:
        ticket = self.get(ticket_id)
        ticket.status = Status.SLEEPING
        ticket.provider = provider
        ticket.sleep_until = _iso_or_string(resume_at)
        ticket.updated_at = _utc_iso(now)
        self.save(ticket)
        return ticket

    def wake_provider(self, provider: str, now: datetime) -> int:
        now_iso = _utc_iso(now)
        woken = 0
        for ticket in self.all():
            if ticket.status is not Status.SLEEPING or ticket.provider != provider:
                continue
            ticket.sleep_until = now_iso
            ticket.updated_at = now_iso
            self.save(ticket)
            woken += 1
        return woken

    def record_tokens(self, ticket_id: str, n: int) -> Ticket:
        ticket = self.get(ticket_id)
        ticket.tokens_used += n
        self.save(ticket)
        return ticket

    def record_pass(self, ticket_id: str, now: datetime) -> Ticket:
        ticket = self.get(ticket_id)
        ticket.status = Status.PASSED
        ticket.updated_at = _utc_iso(now)
        self.save(ticket)
        return ticket

    def mark_running(self, ticket_id: str, now: datetime) -> Ticket:
        ticket = self.get(ticket_id)
        ticket.status = Status.RUNNING
        ticket.sleep_until = None
        ticket.updated_at = _utc_iso(now)
        self.save(ticket)
        return ticket
