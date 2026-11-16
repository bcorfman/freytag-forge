"""Impossible canary tickets for detecting broken factory harnesses."""

from __future__ import annotations

import hashlib
import shlex
from datetime import datetime

from factory.tickets import Station, Ticket, TicketClass, TicketQueue

CANARY_PREFIX = "canary-"


def canary_check(token: str) -> str:
    """Return a shell check whose two required halves cannot both succeed."""

    quoted_token = shlex.quote(token)
    return "\n".join(
        [
            "set -e",
            'if [ ! -f canary.txt ]; then echo "canary check failed: canary.txt is missing" >&2; exit 1; fi',
            "set +e",
            f"grep -Fx -- {quoted_token} canary.txt >/dev/null 2>&1",
            "has_token=$?",
            "set -e",
            'if [ "$has_token" -ne 0 ]; then',
            '  echo "canary check failed: required token line is missing" >&2',
            "  exit 1",
            "fi",
            f"if grep -Fx -- {quoted_token} canary.txt >/dev/null 2>&1; then",
            '  echo "canary check failed: token was present for the forbidden half" >&2',
            "  exit 1",
            "fi",
            'echo "canary check unexpectedly passed" >&2',
            "exit 1",
            "",
        ]
    )


def _token(scene: str) -> str:
    return hashlib.sha256(scene.encode("utf-8")).hexdigest()


def make_canary_tickets(scenes: list[str], now: datetime, *, station: Station | None = None) -> list[Ticket]:
    """Build one deterministic impossible ticket per scene."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    selected_station = station if station is not None else Station.WIRING
    timestamp = now.isoformat()
    tickets: list[Ticket] = []
    for scene in scenes:
        token = _token(scene)
        tickets.append(
            Ticket(
                id=f"{CANARY_PREFIX}{scene}",
                scene=scene,
                station=selected_station,
                token_budget=50_000,
                created_at=timestamp,
                updated_at=timestamp,
                ticket_class=TicketClass.STORY_DATA,
                payload={"canary": True, "check": canary_check(token), "token": token},
            )
        )
    return tickets


def is_canary(ticket: Ticket) -> bool:
    """Return whether a ticket is marked or named as a canary."""

    return ticket.id.startswith(CANARY_PREFIX) or ticket.payload.get("canary") is True


def canary_ids(queue: TicketQueue) -> frozenset[str]:
    """Return IDs of all canary tickets in a queue."""

    return frozenset(ticket.id for ticket in queue.all() if is_canary(ticket))
