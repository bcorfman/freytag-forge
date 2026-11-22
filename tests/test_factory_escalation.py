from datetime import UTC, datetime, timedelta

import pytest

import factory.__main__ as entry
from factory.line import FactoryLine, StationResult
from factory.state import FactoryState
from factory.tickets import LadderRung, Station, Status, Ticket, TicketQueue
from tests.test_factory_preflight import make_config

NOW = datetime(2026, 11, 22, 12, tzinfo=UTC)


class StubNotifier:
    def __init__(self, *, error: Exception | None = None, fail_count: int | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.error = error
        self.fail_count = fail_count

    def notify(self, subject: str, body: str) -> None:
        self.calls.append((subject, body))
        if self.error is not None and (self.fail_count is None or len(self.calls) <= self.fail_count):
            raise self.error


def _history() -> list[dict]:
    return [
        {
            "plan": {"kind": "set_text", "reason": "Precedent: an old clue. Keep the clue."},
            "reasons": "The first payoff was too faint.",
            "fun_advice": "Make the clue matter earlier.",
            "failed_checks": ["delights_the_player"],
        },
        {
            "plan": {"kind": "add_choice", "reason": "Precedent: a prior choice. Add a sharper fork."},
            "reasons": "The second payoff still does not land.",
            "fun_advice": "Give the player a memorable choice.",
            "failed_checks": ["delights_the_player", "has_payoff"],
        },
    ]


def _ticket(tmp_path, *, with_history: bool = True, ladder_rung: LadderRung = LadderRung.OPUS_REFRESH) -> Ticket:
    timestamp = NOW.isoformat()
    payload = {
        "merge_to_main": True,
        "fun_rounds": 1,
        "plan": {"kind": "add_choice", "reason": "Precedent: a prior choice. Add a sharper fork."},
        "fun_lessons_path": str(tmp_path / "fun_lessons.jsonl"),
    }
    if with_history:
        payload["fun_history"] = [_history()[0]]
    return Ticket(
        id="ticket-19h",
        scene="scene-19h",
        station=Station.FUN_REVIEW,
        token_budget=1000,
        created_at=timestamp,
        updated_at=timestamp,
        ladder_rung=ladder_rung,
        payload=payload,
    )


def _blocked_result() -> StationResult:
    return StationResult(
        False,
        "fun_review",
        "fun review blocked the fix",
        payload_updates={
            "fun_review": {
                "verdict": "block",
                "reasons": "The second payoff still does not land.",
                "fun_advice": "Give the player a memorable choice.",
                "failed_checks": ["delights_the_player", "has_payoff"],
            }
        },
    )


def _line(tmp_path, ticket: Ticket, notifier: StubNotifier | None = None) -> tuple[FactoryLine, TicketQueue]:
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "state.json"),
        handlers={Station.FUN_REVIEW: lambda _ticket, _now: _blocked_result()},
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
        notifier=notifier,
    )
    return line, queue


def test_notice_is_sent_once_across_set_aside_return_and_body_has_both_plans(tmp_path) -> None:
    notifier = StubNotifier()
    line, queue = _line(tmp_path, _ticket(tmp_path), notifier)

    assert line.step(NOW).kind == "failed_attempt"
    saved = queue.get("ticket-19h")
    assert saved.status is Status.SET_ASIDE
    assert saved.payload["owner_wait"] == {
        "reason": "fun_review_blocked_twice",
        "since": NOW.isoformat(),
        "reply": None,
    }
    assert saved.payload["owner_notice"] == {"sent_at": NOW.isoformat(), "attempts": 1}
    assert len(notifier.calls) == 1
    subject, body = notifier.calls[0]
    assert subject == "factory: scene scene-19h needs your call (fun review blocked twice, ticket-19h)"
    assert "Stuck: see ticket" in body
    assert "Fix 1 (blocked): set_text: an old clue. Keep the clue." in body
    assert "Fix 2 (blocked): add_choice: a prior choice. Add a sharper fork." in body
    assert "Precedent: " not in body
    assert "Failed: delights_the_player, has_payoff." in body
    assert "Reviewer: The second payoff still does not land." in body
    assert "Last advice: Give the player a memorable choice." in body

    outcomes = line.run(clock=lambda: NOW + timedelta(hours=7), sleep=lambda _seconds: None, max_steps=2)
    assert [outcome.kind for outcome in outcomes] == ["idle"]
    assert len(notifier.calls) == 1
    assert line._next_wake(NOW + timedelta(hours=7)) is None


def test_notifier_exception_does_not_stop_line_and_retries_stop_at_three(tmp_path) -> None:
    notifier = StubNotifier(error=RuntimeError("stub failed"))
    line, queue = _line(tmp_path, _ticket(tmp_path), notifier)
    other = _ticket(tmp_path)
    other.id = "other"
    other.station = Station.ACT_CONTRACTS
    other.created_at = (NOW + timedelta(seconds=1)).isoformat()
    other.updated_at = other.created_at
    queue.add(other)
    line.handlers[Station.ACT_CONTRACTS] = lambda _ticket, _now: StationResult(False, "gate", "bad")

    line.run(clock=lambda: NOW, sleep=lambda _seconds: None, max_steps=4)

    assert len(notifier.calls) == 3
    assert queue.get("ticket-19h").payload["owner_notice"]["attempts"] == 3


def test_failed_notice_retries_on_next_loop_and_success_stops_retries(tmp_path) -> None:
    notifier = StubNotifier(error=RuntimeError("stub failed"), fail_count=1)
    line, queue = _line(tmp_path, _ticket(tmp_path), notifier)
    other = _ticket(tmp_path)
    other.id = "other"
    other.station = Station.ACT_CONTRACTS
    other.created_at = (NOW + timedelta(seconds=1)).isoformat()
    other.updated_at = other.created_at
    queue.add(other)
    line.handlers[Station.ACT_CONTRACTS] = lambda _ticket, _now: StationResult(False, "gate", "bad")

    line.run(clock=lambda: NOW, sleep=lambda _seconds: None, max_steps=4)

    assert len(notifier.calls) == 2
    assert queue.get("ticket-19h").payload["owner_notice"] == {
        "sent_at": NOW.isoformat(),
        "attempts": 2,
    }


def test_notifier_none_still_parks_without_owner_notice(tmp_path) -> None:
    line, queue = _line(tmp_path, _ticket(tmp_path))

    assert line.step(NOW).kind == "failed_attempt"
    saved = queue.get("ticket-19h")
    assert saved.status is Status.SET_ASIDE
    assert saved.payload["owner_wait"]["reply"] is None
    assert "owner_notice" not in saved.payload


def test_ticket_without_two_fun_history_entries_never_notifies(tmp_path) -> None:
    notifier = StubNotifier()
    line, queue = _line(tmp_path, _ticket(tmp_path, with_history=False), notifier)

    assert line.step(NOW).kind == "failed_attempt"
    saved = queue.get("ticket-19h")
    assert saved.status is Status.SET_ASIDE
    assert saved.payload["owner_wait"] == {
        "reason": "fun_review_blocked_twice",
        "since": NOW.isoformat(),
        "reply": None,
    }
    assert "owner_notice" not in saved.payload
    assert notifier.calls == []


@pytest.mark.parametrize(
    "owner_wait",
    [
        {"reason": "manual_hold", "since": NOW.isoformat(), "reply": None},
        {"reason": "fun_review_blocked_twice", "since": NOW.isoformat(), "reply": "retry later"},
    ],
)
def test_retry_skips_unrelated_or_answered_owner_wait_tickets(tmp_path, owner_wait) -> None:
    notifier = StubNotifier()
    ticket = _ticket(tmp_path)
    ticket.status = Status.SET_ASIDE
    ticket.return_after = (NOW + timedelta(hours=1)).isoformat()
    ticket.payload["owner_wait"] = owner_wait
    line, queue = _line(tmp_path, ticket, notifier)

    line.run(clock=lambda: NOW, sleep=lambda _seconds: None, max_steps=1)

    assert notifier.calls == []
    assert "owner_notice" not in queue.get(ticket.id).payload


def test_second_fun_block_forces_set_aside_and_notifies_from_lower_rung(tmp_path) -> None:
    notifier = StubNotifier()
    line, queue = _line(tmp_path, _ticket(tmp_path, ladder_rung=LadderRung.LUNA_RETRY), notifier)

    assert line.step(NOW).kind == "failed_attempt"
    saved = queue.get("ticket-19h")
    assert saved.status is Status.SET_ASIDE
    assert saved.ladder_rung is LadderRung.SET_ASIDE
    assert saved.payload["owner_wait"]["reason"] == "fun_review_blocked_twice"
    assert len(notifier.calls) == 1


def test_owner_wait_ticket_is_skipped_by_all_ready_paths(tmp_path) -> None:
    ticket = _ticket(tmp_path)
    ticket.status = Status.SET_ASIDE
    ticket.return_after = (NOW - timedelta(seconds=1)).isoformat()
    ticket.payload["owner_wait"] = {"reason": "fun_review_blocked_twice", "since": NOW.isoformat(), "reply": None}
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "state.json"),
        handlers={},
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )

    assert line._next_ready(NOW) is None
    assert line._next_wake(NOW) is None
    assert queue.next_ready(NOW) is None


def test_owner_state_survives_ticket_save_and_load(tmp_path) -> None:
    queue = TicketQueue(tmp_path / "tickets")
    ticket = _ticket(tmp_path)
    ticket.payload["owner_wait"] = {"reason": "fun_review_blocked_twice", "since": NOW.isoformat(), "reply": None}
    ticket.payload["owner_notice"] = {"sent_at": NOW.isoformat(), "attempts": 1}
    queue.add(ticket)
    loaded = queue.get(ticket.id)
    queue.save(loaded)
    reloaded = TicketQueue(tmp_path / "tickets").get(ticket.id)

    assert reloaded.payload["owner_wait"] == ticket.payload["owner_wait"]
    assert reloaded.payload["owner_notice"] == ticket.payload["owner_notice"]


def test_main_passes_built_notifier_to_factory_line(tmp_path, monkeypatch) -> None:
    config = make_config(tmp_path)
    marker = tmp_path / "factory/state/preflight.ok"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("successful preflight\n", encoding="utf-8")
    entry._SUCCESSFUL_PREFLIGHTS.add(marker.resolve())
    seen: dict[str, object] = {}

    class RecordingLine:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def run(self, **_kwargs):
            return []

    monkeypatch.setattr(entry, "FactoryLine", RecordingLine)
    monkeypatch.setattr(entry, "_handlers", lambda _spec: {})
    monkeypatch.setattr(entry, "guarded_run", lambda function, **_kwargs: function())

    assert (
        entry.main(
            ["--root", str(tmp_path), "--config", str(config), "run", "--handlers", "stub:handlers"],
            now_fn=lambda: NOW,
        )
        == 0
    )
    assert seen["notifier"].__class__.__name__ == "FileNotifier"
