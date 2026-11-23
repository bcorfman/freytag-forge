from datetime import UTC, datetime

import pytest

from factory.line import MAX_PROBE_ROUNDS, FactoryLine, StationResult
from factory.state import FactoryState
from factory.stations import probe
from factory.tickets import LadderRung, Station, Status, Ticket, TicketQueue

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def make_ticket(ticket_id: str, station: Station, payload: dict | None = None) -> Ticket:
    timestamp = NOW.isoformat()
    return Ticket(
        id=ticket_id,
        scene="1A",
        station=station,
        token_budget=1000,
        created_at=timestamp,
        updated_at=timestamp,
        payload=payload or {},
    )


def make_line(tmp_path, ticket: Ticket, handler) -> tuple[FactoryLine, TicketQueue]:
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "state.json"),
        handlers={ticket.station: handler},
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )
    return line, queue


def probe_verdict(verdict: str) -> StationResult:
    return StationResult(
        False,
        "probe",
        f"{verdict}: evidence",
        payload_updates={
            "probe": {
                "verdict": verdict,
                "feedback": f"verdict {verdict} control 1 2 0 0 0 0 candidate 2 2 0 0 0 0",
            }
        },
    )


def test_prompt_snapshot_routes_merge_to_probe_and_other_tickets_to_live_playtest(tmp_path) -> None:
    merge_line, merge_queue = make_line(
        tmp_path / "merge",
        make_ticket("merge", Station.PROMPT_SNAPSHOT, {"merge_to_main": True}),
        lambda _ticket, _now: StationResult(True, "snapshot", "ok"),
    )
    ordinary_line, ordinary_queue = make_line(
        tmp_path / "ordinary",
        make_ticket("ordinary", Station.PROMPT_SNAPSHOT),
        lambda _ticket, _now: StationResult(True, "snapshot", "ok"),
    )

    assert merge_line.step(NOW).kind == "advanced"
    assert merge_queue.get("merge").station is Station.PROBE
    assert ordinary_line.step(NOW).kind == "advanced"
    assert ordinary_queue.get("ordinary").station is Station.LIVE_PLAYTEST


def test_probe_passes_to_fun_review_and_clears_retry_feedback(tmp_path) -> None:
    ticket = make_ticket(
        "probe-pass",
        Station.PROBE,
        {
            "merge_to_main": True,
            "plan": {"kind": "set_text"},
            "feedback_plan": {"kind": "old"},
            "probe_feedback": "verdict reject control 1 2 0 0 0 0 candidate 2 2 0 0 0 0",
        },
    )
    line, queue = make_line(
        tmp_path,
        ticket,
        lambda _ticket, _now: StationResult(
            True,
            "probe",
            "keep: evidence",
            payload_updates={"probe": {"verdict": "keep"}},
        ),
    )

    assert line.step(NOW).kind == "advanced"
    saved = queue.get("probe-pass")
    assert saved.station is Station.FUN_REVIEW
    assert "feedback_plan" not in saved.payload
    assert "probe_feedback" not in saved.payload
    assert saved.payload["probe"]["verdict"] == "keep"


def test_diagnose_still_routes_to_wiring(tmp_path) -> None:
    line, queue = make_line(
        tmp_path,
        make_ticket("diagnose", Station.DIAGNOSE),
        lambda _ticket, _now: StationResult(True, "diagnose", "ok"),
    )

    assert line.step(NOW).kind == "advanced"
    assert queue.get("diagnose").station is Station.WIRING


@pytest.mark.parametrize("round_number", [0, 1])
@pytest.mark.parametrize("verdict", ["reject", "inconclusive"])
def test_probe_verdict_retry_preserves_failure_fields_and_requeues_wiring(tmp_path, round_number, verdict) -> None:
    old_plan = {"kind": "set_text", "reason": "old"}
    ticket = make_ticket(
        f"probe-{verdict}-{round_number}",
        Station.PROBE,
        {"plan": old_plan, "probe_rounds": round_number, "provider": "alpha"},
    )
    line, queue = make_line(tmp_path, ticket, lambda _ticket, _now: probe_verdict(verdict))
    before = queue.get(ticket.id)
    before_failure_fields = (
        before.attempts,
        before.tokens_used,
        [(item.check, item.output_hash) for item in before.failures],
    )

    outcome = line.step(NOW)

    saved = queue.get(ticket.id)
    assert outcome.kind == "probe_rejected"
    assert saved.station is Station.WIRING
    assert saved.status is Status.QUEUED
    assert saved.attempts == 0
    assert saved.ladder_rung is LadderRung.LUNA_RETRY
    assert saved.provider is None
    assert saved.sleep_until is None
    assert saved.return_after is None
    assert saved.payload["probe_rounds"] == round_number + 1
    assert saved.payload["feedback_plan"] == old_plan
    assert saved.payload["probe_feedback"].startswith(f"verdict {verdict}")
    assert saved.payload["probe"]["verdict"] == verdict
    assert "plan" not in saved.payload
    assert (saved.attempts, saved.tokens_used, [(item.check, item.output_hash) for item in saved.failures]) == (
        before_failure_fields
    )


def test_probe_rejection_preserves_consumed_approval_when_replanning(tmp_path) -> None:
    ticket = make_ticket(
        "probe-consumed-reject",
        Station.PROBE,
        {
            "plan": {"kind": "set_text", "reason": "old"},
            "probe_rounds": 0,
            "billed_run_approved": True,
            "billed_run_approval_id": "a1",
        },
    )

    def reject_probe(_ticket, _now):
        result = probe_verdict("reject")
        result.payload_updates = {
            **(result.payload_updates or {}),
            "billed_run_approved": False,
            "billed_runs_consumed": 1,
            "billed_run_consumed_approval_id": "a1",
        }
        return result

    line, queue = make_line(tmp_path, ticket, reject_probe)

    assert line.step(NOW).kind == "probe_rejected"
    saved = queue.get(ticket.id)
    assert saved.station is Station.WIRING
    assert saved.payload["billed_run_approved"] is False
    assert saved.payload["billed_runs_consumed"] == 1
    assert saved.payload["billed_run_consumed_approval_id"] == "a1"
    assert probe._approval_error(saved.payload)

    reapproved = {**saved.payload, "billed_run_approved": True}
    assert probe._approval_error(reapproved)
    assert probe._approval_error({**reapproved, "billed_run_approval_id": "a2"}) is None


def test_third_probe_reject_uses_ladder_to_set_aside_and_records_evidence(tmp_path) -> None:
    ticket = make_ticket("probe-third", Station.PROBE, {"probe_rounds": MAX_PROBE_ROUNDS - 1})
    line, queue = make_line(tmp_path, ticket, lambda _ticket, _now: probe_verdict("reject"))

    outcome = line.step(NOW)

    saved = queue.get("probe-third")
    assert outcome.kind == "failed_attempt"
    assert saved.status is Status.SET_ASIDE
    assert saved.ladder_rung is LadderRung.SET_ASIDE
    assert saved.attempts == 0
    assert saved.return_after is not None
    assert saved.failures[-1].check == "probe"
    assert saved.payload["probe"]["verdict"] == "reject"


def test_probe_infrastructure_failure_is_a_normal_failure_not_a_round(tmp_path) -> None:
    ticket = make_ticket("probe-infra", Station.PROBE)
    line, queue = make_line(
        tmp_path,
        ticket,
        lambda _ticket, _now: StationResult(False, "probe", "runner failed: unavailable"),
    )

    assert line.step(NOW).kind == "failed_attempt"
    saved = queue.get("probe-infra")
    assert saved.status is Status.QUEUED
    assert saved.attempts == 1
    assert saved.failures[-1].check == "probe"
    assert "probe_rounds" not in saved.payload


def test_merge_ticket_walks_prompt_probe_fun_review_and_deliver(tmp_path) -> None:
    ticket = make_ticket("walk-merge", Station.PROMPT_SNAPSHOT, {"merge_to_main": True})
    handlers = {
        Station.PROMPT_SNAPSHOT: lambda _ticket, _now: StationResult(True, "snapshot", "ok"),
        Station.PROBE: lambda _ticket, _now: StationResult(True, "probe", "ok"),
        Station.FUN_REVIEW: lambda _ticket, _now: StationResult(True, "fun_review", "ok"),
        Station.DELIVER: lambda _ticket, _now: StationResult(True, "deliver", "ok"),
        Station.LIVE_PLAYTEST: lambda _ticket, _now: StationResult(True, "live_playtest", "ok"),
    }
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "state.json"),
        handlers=handlers,
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )

    assert [line.step(NOW).kind for _ in range(5)] == ["advanced", "advanced", "advanced", "advanced", "delivered"]
    assert queue.get("walk-merge").status is Status.PASSED


def test_fun_feedback_sendback_rechecks_through_probe_before_fun_review(tmp_path) -> None:
    ticket = make_ticket(
        "fun-route",
        Station.FUN_REVIEW,
        {
            "merge_to_main": True,
            "plan": {"kind": "set_text", "address": "first"},
        },
    )
    fun_calls = 0

    def fun_review(_ticket, _now):
        nonlocal fun_calls
        fun_calls += 1
        if fun_calls == 1:
            return StationResult(
                False,
                "fun_review",
                "blocked",
                payload_updates={
                    "fun_review": {
                        "verdict": "block",
                        "reasons": "Use the existing detail.",
                        "fun_advice": "Make the existing detail do more work.",
                        "failed_checks": ["delights_the_player"],
                        "plan": {"kind": "set_text", "address": "first"},
                    }
                },
            )
        return StationResult(True, "fun_review", "pass")

    handlers = {
        Station.FUN_REVIEW: fun_review,
        Station.WIRING: lambda _ticket, _now: StationResult(True, "wiring", "ok"),
        Station.FREE_GATES: lambda _ticket, _now: StationResult(True, "free_gates", "ok"),
        Station.PROMPT_SNAPSHOT: lambda _ticket, _now: StationResult(True, "snapshot", "ok"),
        Station.PROBE: lambda _ticket, _now: StationResult(True, "probe", "ok"),
        Station.DELIVER: lambda _ticket, _now: StationResult(True, "deliver", "ok"),
        Station.LIVE_PLAYTEST: lambda _ticket, _now: StationResult(True, "live_playtest", "ok"),
    }
    line, queue = make_line(tmp_path, ticket, handlers[Station.FUN_REVIEW])
    line.handlers = handlers

    assert line.step(NOW).kind == "fun_blocked"
    saved = queue.get(ticket.id)
    assert saved.station is Station.WIRING
    assert "plan" not in saved.payload

    assert line.step(NOW).kind == "advanced"
    assert queue.get(ticket.id).station is Station.FREE_GATES
    assert line.step(NOW).kind == "advanced"
    assert queue.get(ticket.id).station is Station.PROMPT_SNAPSHOT
    assert line.step(NOW).kind == "advanced"
    assert queue.get(ticket.id).station is Station.PROBE
    assert line.step(NOW).kind == "advanced"
    assert queue.get(ticket.id).station is Station.FUN_REVIEW
    assert line.step(NOW).kind == "advanced"
    assert queue.get(ticket.id).station is Station.DELIVER
    assert fun_calls == 2
