import sys
from datetime import UTC, datetime, timedelta

import pytest

from factory.breakers import (
    BreakerConfig,
    BreakerTrip,
    CommandNotifier,
    FileNotifier,
    check_breakers,
    guarded_run,
    trip_all,
)
from factory.guard import Caps, SpendLedger, Usage
from factory.state import FactoryState
from factory.tickets import Failure, Station, Status, Ticket, TicketQueue

NOW = datetime(2026, 11, 15, 12, tzinfo=UTC)


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def notify(self, subject: str, body: str) -> None:
        self.calls.append((subject, body))


def _caps(total: float = 100.0, rate: float = 100.0) -> Caps:
    return Caps(total, {}, [], 3600, rate)


def _ticket(ticket_id: str, *, status: Status = Status.QUEUED, tokens: int = 0) -> Ticket:
    stamp = NOW.isoformat()
    return Ticket(ticket_id, "scene", Station.PROSE, 1000, stamp, stamp, status=status, tokens_used=tokens)


def _setup(tmp_path):
    queue = TicketQueue(tmp_path / "queue")
    state = FactoryState.load(tmp_path / "state.json")
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    return queue, state, ledger


def _check(tmp_path, *, caps=None, config=None, **kwargs):
    queue, state, ledger = _setup(tmp_path)
    return (
        check_breakers(
            queue=queue,
            state=state,
            ledger=ledger,
            caps=caps or _caps(),
            config=config or BreakerConfig(),
            now=NOW,
            **kwargs,
        ),
        queue,
        state,
        ledger,
    )


def _record(ledger: SpendLedger, *, usd: float, at: datetime = NOW) -> None:
    ledger.record(Usage(at, "provider", "model", "station", "scene", "ticket", 10, usd))


def test_budget_spent_trips_at_cap(tmp_path):
    trips, _, _, ledger = _check(tmp_path, caps=_caps(total=1.0))
    _record(ledger, usd=1.0)
    trips, *_ = _check(tmp_path, caps=_caps(total=1.0))
    assert [trip.name for trip in trips] == ["budget_spent"]


def test_budget_one_cent_under_does_not_trip(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    _record(ledger, usd=0.99)
    assert (
        check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(total=1.0), config=BreakerConfig(), now=NOW)
        == []
    )


def test_delivered_suppresses_budget_breaker(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    _record(ledger, usd=1.0)
    trips = check_breakers(
        queue=queue, state=state, ledger=ledger, caps=_caps(total=1.0), config=BreakerConfig(), now=NOW, delivered=True
    )
    assert trips == []


def test_spend_rate_trips_above_cap(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    _record(ledger, usd=1.01)
    trips = check_breakers(
        queue=queue, state=state, ledger=ledger, caps=_caps(rate=1.0), config=BreakerConfig(), now=NOW
    )
    assert [trip.name for trip in trips] == ["spend_rate"]


def test_repeat_failure_trips_after_three_matching_failures(tmp_path):
    trips, queue, _, _ = _check(tmp_path, config=BreakerConfig(repeat_failures=3))
    ticket = _ticket("repeat")
    ticket.failures = [Failure("judge", "hash", str(index)) for index in range(3)]
    queue.add(ticket)
    trips = check_breakers(
        queue=queue,
        state=FactoryState.load(tmp_path / "state.json"),
        ledger=SpendLedger(tmp_path / "ledger.jsonl"),
        caps=_caps(),
        config=BreakerConfig(),
        now=NOW,
    )
    assert [trip.name for trip in trips] == ["repeat_failure"]
    assert "repeat" in trips[0].reason


def test_two_consecutive_failures_do_not_trip(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    ticket = _ticket("repeat")
    ticket.failures = [Failure("judge", "hash", "1"), Failure("judge", "hash", "2")]
    queue.add(ticket)
    assert check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=BreakerConfig(), now=NOW) == []


def test_different_check_breaks_failure_streak(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    ticket = _ticket("repeat")
    ticket.failures = [Failure("judge", "hash", "1"), Failure("other", "hash", "2"), Failure("judge", "hash", "3")]
    queue.add(ticket)
    assert check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=BreakerConfig(), now=NOW) == []


def test_different_output_breaks_failure_streak(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    ticket = _ticket("repeat")
    ticket.failures = [Failure("judge", "hash", "1"), Failure("judge", "other", "2"), Failure("judge", "hash", "3")]
    queue.add(ticket)
    assert check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=BreakerConfig(), now=NOW) == []


def test_token_outlier_requires_minimum_sample(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    for index, tokens in enumerate([1, 1, 1, 1]):
        queue.add(_ticket(f"token-{index}", tokens=tokens))
    queue.add(_ticket("outlier", tokens=100))
    config = BreakerConfig(min_tickets_for_median=6)
    assert check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=config, now=NOW) == []


def test_token_outlier_trips_with_enough_tickets(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    for index, tokens in enumerate([10, 10, 10, 10, 10]):
        queue.add(_ticket(f"token-{index}", tokens=tokens))
    queue.add(_ticket("outlier", tokens=51))
    trips = check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=BreakerConfig(), now=NOW)
    assert [trip.name for trip in trips] == ["token_outlier"]


def test_sleeping_ticket_does_not_trip_ticket_breakers(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    sleeping = _ticket("sleeping", status=Status.SLEEPING, tokens=1000)
    sleeping.failures = [Failure("judge", "hash", str(index)) for index in range(3)]
    queue.add(sleeping)
    assert check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=BreakerConfig(), now=NOW) == []


def test_provider_overdue_trips_at_deadline(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    state.lanes["provider"] = (NOW - timedelta(seconds=86400)).isoformat()
    trips = check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=BreakerConfig(), now=NOW)
    assert [trip.name for trip in trips] == ["provider_overdue"]


def test_provider_one_second_before_overdue_does_not_trip(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    state.lanes["provider"] = (NOW - timedelta(seconds=86399)).isoformat()
    assert check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=BreakerConfig(), now=NOW) == []


def test_sleeping_lane_does_not_trip_before_overdue(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    state.lanes["provider"] = (NOW - timedelta(seconds=3600)).isoformat()
    assert check_breakers(queue=queue, state=state, ledger=ledger, caps=_caps(), config=BreakerConfig(), now=NOW) == []


def test_canary_passed_trips(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    queue.add(_ticket("canary", status=Status.PASSED))
    trips = check_breakers(
        queue=queue,
        state=state,
        ledger=ledger,
        caps=_caps(),
        config=BreakerConfig(),
        now=NOW,
        canary_ids=frozenset({"canary"}),
    )
    assert [trip.name for trip in trips] == ["canary_passed"]


def test_harness_changed_lists_at_most_five_paths(tmp_path):
    trips, *_ = _check(tmp_path, frozen_touched=tuple(f"path-{index}" for index in range(7)))
    assert [trip.name for trip in trips] == ["harness_changed"]
    assert trips[0].reason.count("path-") == 5


def test_trip_order_is_fixed(tmp_path):
    queue, state, ledger = _setup(tmp_path)
    _record(ledger, usd=2.0)
    queue.add(_ticket("canary", status=Status.PASSED))
    for index in range(5):
        queue.add(_ticket(f"token-{index}", tokens=1))
    state.lanes["provider"] = (NOW - timedelta(seconds=86400)).isoformat()
    trips = check_breakers(
        queue=queue,
        state=state,
        ledger=ledger,
        caps=_caps(total=1.0, rate=1.0),
        config=BreakerConfig(),
        now=NOW,
        frozen_touched=("frozen.py",),
        canary_ids=frozenset({"canary"}),
    )
    assert [trip.name for trip in trips] == [
        "budget_spent",
        "spend_rate",
        "provider_overdue",
        "canary_passed",
        "harness_changed",
    ]


def test_trip_all_notifies_once_across_two_calls(tmp_path):
    state = FactoryState.load(tmp_path / "state.json")
    notifier = RecordingNotifier()
    trips = [BreakerTrip("budget_spent", "budget reached.")]
    assert trip_all(trips, state=state, notifier=notifier, now=NOW) is True
    assert trip_all(trips, state=state, notifier=notifier, now=NOW) is True
    assert len(notifier.calls) == 1
    assert state.is_tripped()


def test_trip_all_empty_returns_false(tmp_path):
    state = FactoryState.load(tmp_path / "state.json")
    notifier = RecordingNotifier()
    assert trip_all([], state=state, notifier=notifier, now=NOW) is False
    assert notifier.calls == []


def test_file_notifier_appends_timestamp_free_block(tmp_path):
    path = tmp_path / "nested" / "notifications.txt"
    FileNotifier(path).notify("subject", "body")
    assert path.read_text(encoding="utf-8") == "subject\nbody\n\n"


def test_command_notifier_accepts_harmless_command():
    notifier = CommandNotifier([sys.executable, "-c", "import sys; sys.exit(0)"])
    notifier.notify("subject", "body")
    assert notifier.last_error is None


def test_command_notifier_records_failure_without_raising():
    notifier = CommandNotifier([sys.executable, "-c", "import sys; sys.exit(3)"])
    notifier.notify("subject", "body")
    assert isinstance(notifier.last_error, Exception)


def test_guarded_run_trips_and_reraises(tmp_path):
    state = FactoryState.load(tmp_path / "state.json")
    notifier = RecordingNotifier()

    with pytest.raises(ValueError, match="broken"):
        guarded_run(
            lambda: (_ for _ in ()).throw(ValueError("broken")), state=state, notifier=notifier, now_fn=lambda: NOW
        )

    assert notifier.calls[0][0] == "factory stopped: crash"
    assert "ValueError: broken" in state.breaker_reason()


def test_guarded_run_does_not_catch_keyboard_interrupt(tmp_path):
    state = FactoryState.load(tmp_path / "state.json")
    notifier = RecordingNotifier()

    def interrupt():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        guarded_run(interrupt, state=state, notifier=notifier, now_fn=lambda: NOW)
    assert notifier.calls == []
