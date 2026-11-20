import json
from datetime import UTC, datetime, timedelta

import pytest

from factory.tickets import (
    Failure,
    LadderRung,
    Station,
    Status,
    Ticket,
    TicketClass,
    TicketQueue,
    output_hash,
    repeat_failure_count,
)

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def make_ticket(ticket_id: str, created_at: str | None = None) -> Ticket:
    timestamp = created_at or NOW.isoformat()
    return Ticket(
        id=ticket_id,
        scene="opening",
        station=Station.PROSE,
        token_budget=1000,
        created_at=timestamp,
        updated_at=timestamp,
        ticket_class=TicketClass.NARRATOR_PROMPT,
        payload={"beats": ["arrive"], "active": True},
    )


def test_ticket_round_trip_is_exact_and_json_serialisable() -> None:
    ticket = make_ticket("t1")
    ticket.failures.append(Failure("check", output_hash("bad"), NOW.isoformat()))
    encoded = ticket.to_dict()
    json.dumps(encoded)
    assert Ticket.from_dict(encoded).to_dict() == encoded


def test_duplicate_add_raises(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    queue.add(make_ticket("t1"))
    with pytest.raises(ValueError):
        queue.add(make_ticket("t1"))


def test_next_ready_orders_by_created_at_then_id(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    queue.add(make_ticket("b", (NOW + timedelta(minutes=1)).isoformat()))
    queue.add(make_ticket("a", NOW.isoformat()))
    assert queue.next_ready(NOW).id == "a"


def test_next_ready_accepts_queued_tickets(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    queue.add(make_ticket("queued"))
    assert queue.next_ready(NOW).id == "queued"


def test_next_ready_wakes_sleeping_ticket_at_deadline(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    ticket = make_ticket("sleeping")
    ticket.status = Status.SLEEPING
    ticket.sleep_until = (NOW + timedelta(seconds=1)).isoformat()
    queue.add(ticket)
    assert queue.next_ready(NOW) is None
    assert queue.next_ready(NOW + timedelta(seconds=1)).id == "sleeping"


def test_next_ready_wakes_set_aside_ticket_at_deadline(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    ticket = make_ticket("set-aside")
    ticket.status = Status.SET_ASIDE
    ticket.return_after = (NOW + timedelta(seconds=1)).isoformat()
    queue.add(ticket)
    assert queue.next_ready(NOW) is None
    assert queue.next_ready(NOW + timedelta(seconds=1)).id == "set-aside"


def test_next_ready_skips_running_tickets(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    ticket = make_ticket("running")
    ticket.status = Status.RUNNING
    queue.add(ticket)
    assert queue.next_ready(NOW) is None


def test_full_ladder_climbs_after_exact_attempt_counts(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    queue.add(make_ticket("ladder"))
    for rung in (LadderRung.LUNA_RETRY, LadderRung.SONNET_REWRITE, LadderRung.OPUS_REFRESH):
        for attempt in range(1, 4):
            ticket = queue.record_failure("ladder", "gate", f"bad-{rung}-{attempt}", NOW)
            if attempt < 3:
                assert ticket.ladder_rung == rung
                assert ticket.attempts == attempt
                assert ticket.status is Status.QUEUED
            else:
                assert ticket.attempts == 0
                assert ticket.ladder_rung == LadderRung(rung + 1)
    ticket = queue.get("ladder")
    assert ticket.status is Status.SET_ASIDE
    assert ticket.return_after == (NOW + timedelta(hours=6)).isoformat()


def test_set_aside_failure_stays_set_aside_and_reschedules(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    ticket = make_ticket("set-aside")
    ticket.status = Status.SET_ASIDE
    ticket.ladder_rung = LadderRung.SET_ASIDE
    queue.add(ticket)
    updated = queue.record_failure("set-aside", "gate", "bad", NOW)
    assert updated.status is Status.SET_ASIDE
    assert updated.return_after == (NOW + timedelta(hours=6)).isoformat()


def test_limit_hit_does_not_change_attempts_or_failures(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    ticket = make_ticket("limited")
    ticket.attempts = 2
    ticket.failures.append(Failure("gate", output_hash("bad"), NOW.isoformat()))
    queue.add(ticket)
    resume_at = NOW + timedelta(minutes=5)
    queue.record_limit_hit("limited", "luna", resume_at, NOW)
    limited = queue.get("limited")
    assert limited.status is Status.SLEEPING
    assert limited.provider == "luna"
    assert limited.sleep_until == resume_at.isoformat()
    assert limited.attempts == 2
    assert limited.failures == ticket.failures
    assert queue.next_ready(NOW + timedelta(minutes=4, seconds=59)) is None
    assert queue.next_ready(resume_at).id == "limited"


def test_wake_provider_wakes_only_matching_sleeping_tickets(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    matching = make_ticket("matching")
    matching.status = Status.SLEEPING
    matching.provider = "codex"
    matching.sleep_until = (NOW + timedelta(hours=1)).isoformat()
    other = make_ticket("other")
    other.status = Status.SLEEPING
    other.provider = "claude"
    other.sleep_until = (NOW + timedelta(hours=1)).isoformat()
    queued = make_ticket("queued")
    queue.add(matching)
    queue.add(other)
    queue.add(queued)

    woken = queue.wake_provider("codex", NOW)

    assert woken == 1
    assert queue.get("matching").sleep_until == NOW.isoformat()
    assert queue.get("matching").updated_at == NOW.isoformat()
    assert queue.get("other").sleep_until == (NOW + timedelta(hours=1)).isoformat()
    assert queue.get("queued").status is Status.QUEUED


def test_repeat_failure_count_uses_only_the_final_signature() -> None:
    failures = [
        Failure("gate", output_hash("one"), "a"),
        Failure("gate", output_hash("two"), "b"),
        Failure("gate", output_hash("one"), "c"),
        Failure("gate", output_hash("one"), "d"),
    ]
    assert repeat_failure_count(Ticket("t", "s", Station.PROSE, 1, "a", "a", failures=failures)) == 2
    assert repeat_failure_count(Ticket("empty", "s", Station.PROSE, 1, "a", "a")) == 0


def test_atomic_ticket_writes_leave_no_temp_files(tmp_path) -> None:
    queue = TicketQueue(tmp_path)
    queue.add(make_ticket("atomic"))
    queue.record_pass("atomic", NOW)
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob(".*.tmp")) == []
