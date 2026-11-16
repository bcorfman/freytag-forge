from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from factory.breakers import BreakerConfig, check_breakers
from factory.checks.canary import (
    CANARY_PREFIX,
    canary_check,
    canary_ids,
    is_canary,
    make_canary_tickets,
)
from factory.guard import Caps, SpendLedger
from factory.state import FactoryState
from factory.tickets import Ticket, TicketClass, TicketQueue


def _run(script: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["/bin/sh", "-c", script], cwd=cwd, check=False, capture_output=True, text=True)


def test_canary_check_fails_for_missing_present_and_absent_token(tmp_path: Path) -> None:
    token = "exact-token"

    assert _run(canary_check(token), tmp_path).returncode != 0
    (tmp_path / "canary.txt").write_text(token + "\n", encoding="utf-8")
    assert _run(canary_check(token), tmp_path).returncode != 0
    (tmp_path / "canary.txt").write_text("different-token\n", encoding="utf-8")
    assert _run(canary_check(token), tmp_path).returncode != 0


def test_canary_tickets_are_deterministic_and_have_required_fields() -> None:
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    first = make_canary_tickets(["scene-a", "scene-b"], now)
    second = make_canary_tickets(["scene-a", "scene-b"], now)

    assert [ticket.to_dict() for ticket in first] == [ticket.to_dict() for ticket in second]
    assert all(ticket.id == f"{CANARY_PREFIX}{ticket.scene}" for ticket in first)
    assert all(ticket.station.value == 4 for ticket in first)
    assert all(ticket.token_budget == 50_000 for ticket in first)
    assert all(ticket.ticket_class is TicketClass.STORY_DATA for ticket in first)
    assert all(ticket.created_at == now.isoformat() for ticket in first)
    assert all(ticket.updated_at == now.isoformat() for ticket in first)
    assert all(ticket.payload["canary"] is True for ticket in first)
    assert all(ticket.payload["token"] for ticket in first)
    assert all(is_canary(ticket) for ticket in first)


def test_canary_ids_and_breaker_trip(tmp_path: Path) -> None:
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    queue = TicketQueue(tmp_path / "queue")
    canary = make_canary_tickets(["scene-a"], now)[0]
    named = Ticket(
        id="ordinary-canary-payload",
        scene="scene-b",
        station=canary.station,
        token_budget=100,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        payload={"canary": True},
    )
    queue.add(canary)
    queue.add(named)
    assert canary_ids(queue) == frozenset({canary.id, named.id})

    queue.record_pass(canary.id, now)
    caps = Caps.from_dict(
        {
            "total_budget_usd": 1_000_000,
            "daily_cap_usd": {"provider": 1_000_000},
            "call_caps": [],
            "rate_window_s": 3600,
            "rate_max_usd": 1_000_000,
        }
    )
    trips = check_breakers(
        queue=queue,
        state=FactoryState.load(tmp_path / "state.json"),
        ledger=SpendLedger(tmp_path / "ledger.jsonl"),
        caps=caps,
        config=BreakerConfig(),
        now=now,
        canary_ids=canary_ids(queue),
    )

    assert any(trip.name == "canary_passed" for trip in trips)
