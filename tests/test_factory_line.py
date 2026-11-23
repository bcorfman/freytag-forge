from datetime import UTC, datetime, timedelta

import pytest

from factory.breakers import BreakerConfig, check_breakers
from factory.guard import Caps, LimitSleep, SpendLedger
from factory.line import FactoryLine, StationResult
from factory.state import FactoryState
from factory.tickets import LadderRung, Station, Status, Ticket, TicketQueue

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def make_ticket(ticket_id: str, station: Station = Station.ACT_CONTRACTS, created_at: datetime = NOW) -> Ticket:
    timestamp = created_at.isoformat()
    return Ticket(
        id=ticket_id,
        scene="scene",
        station=station,
        token_budget=1000,
        created_at=timestamp,
        updated_at=timestamp,
        payload={"provider": "alpha"},
    )


def make_line(
    tmp_path,
    tickets: list[Ticket],
    handlers: dict[Station, object],
    provider_for=None,
    check_breakers=None,
    **options,
) -> tuple[FactoryLine, TicketQueue, FactoryState]:
    queue = TicketQueue(tmp_path / "tickets")
    for ticket in tickets:
        queue.add(ticket)
    state = FactoryState.load(tmp_path / "state.json")
    line = FactoryLine(
        queue=queue,
        state=state,
        handlers=handlers,
        provider_for=provider_for or (lambda ticket: ticket.payload.get("provider")),
        check_breakers=check_breakers or (lambda now: []),
        **options,
    )
    return line, queue, state


def passing(ticket, now):
    return StationResult(True, "pass", "ok")


def failing(ticket, now):
    return StationResult(False, "quality", "bad")


def test_ticket_walks_all_stations_and_is_delivered(tmp_path):
    ticket = make_ticket("walk")
    handlers = {station: passing for station in Station}
    line, queue, _ = make_line(tmp_path, [ticket], handlers)

    outcomes = [line.step(NOW) for _ in range(9)]

    assert [outcome.kind for outcome in outcomes] == ["advanced"] * 8 + ["delivered"]
    assert queue.get("walk").status is Status.PASSED


def test_live_playtest_failure_with_turns_moves_to_triage(tmp_path):
    ticket = make_ticket("triage", station=Station.LIVE_PLAYTEST)
    ticket.attempts = 2
    ticket.ladder_rung = LadderRung.OPUS_REFRESH
    ticket.sleep_until = (NOW + timedelta(hours=1)).isoformat()
    ticket.return_after = (NOW + timedelta(hours=2)).isoformat()
    turns = [{"key": "1A/r2/t1", "scene": "1A", "stuck": True}]
    line, queue, _ = make_line(
        tmp_path,
        [ticket],
        {Station.LIVE_PLAYTEST: lambda ticket, now: StationResult(False, "playtest", "bad", turns=turns)},
    )

    outcome = line.step(NOW)

    saved = queue.get("triage")
    assert outcome.kind == "to_triage"
    assert saved.station is Station.TRIAGE
    assert saved.status is Status.QUEUED
    assert saved.attempts == 0
    assert saved.ladder_rung is LadderRung.LUNA_RETRY
    assert saved.provider is None
    assert saved.sleep_until is None
    assert saved.return_after is None
    assert saved.payload["provider"] == "alpha"
    assert saved.payload["turns"] == turns


def test_merge_ticket_delivers_after_probe_and_keeps_payload_updates(tmp_path):
    ticket = make_ticket("merge", station=Station.PROMPT_SNAPSHOT)
    ticket.payload["merge_to_main"] = True

    def delivery(_ticket, _now):
        return StationResult(True, "deliver", "merged", payload_updates={"merged_sha": "abc"})

    line, queue, _ = make_line(
        tmp_path,
        [ticket],
        {
            Station.PROMPT_SNAPSHOT: passing,
            Station.PROBE: passing,
            Station.FUN_REVIEW: passing,
            Station.DELIVER: delivery,
            Station.LIVE_PLAYTEST: passing,
        },
    )

    assert line.step(NOW).kind == "advanced"
    assert queue.get("merge").station is Station.PROBE
    assert line.step(NOW).kind == "advanced"
    assert queue.get("merge").station is Station.FUN_REVIEW
    assert line.step(NOW).kind == "advanced"
    assert queue.get("merge").station is Station.DELIVER
    assert line.step(NOW).kind == "advanced"
    saved = queue.get("merge")
    assert saved.station is Station.LIVE_PLAYTEST
    assert saved.payload["merged_sha"] == "abc"
    assert line.step(NOW).kind == "delivered"
    assert queue.get("merge").status is Status.PASSED


@pytest.mark.parametrize("merge_to_main", [False, True])
def test_diagnose_pass_always_routes_to_wiring_and_resets_attempts(tmp_path, merge_to_main):
    ticket = make_ticket("diagnose", station=Station.DIAGNOSE)
    ticket.payload["merge_to_main"] = merge_to_main
    ticket.attempts = 2
    ticket.ladder_rung = LadderRung.OPUS_REFRESH
    ticket.provider = "old-provider"
    ticket.sleep_until = (NOW + timedelta(hours=1)).isoformat()
    ticket.return_after = (NOW + timedelta(hours=2)).isoformat()
    line, queue, _ = make_line(tmp_path, [ticket], {Station.DIAGNOSE: passing})

    assert line.step(NOW).kind == "advanced"

    saved = queue.get("diagnose")
    assert saved.station is Station.WIRING
    assert saved.status is Status.QUEUED
    assert saved.attempts == 0
    assert saved.ladder_rung is LadderRung.LUNA_RETRY
    assert saved.provider is None
    assert saved.sleep_until is None
    assert saved.return_after is None


def test_failed_diagnose_records_failure_and_stays_at_diagnose(tmp_path):
    ticket = make_ticket("diagnose-fail", station=Station.DIAGNOSE)
    line, queue, _ = make_line(tmp_path, [ticket], {Station.DIAGNOSE: failing})

    assert line.step(NOW).kind == "failed_attempt"

    saved = queue.get("diagnose-fail")
    assert saved.station is Station.DIAGNOSE
    assert saved.failures[-1].check == "quality"


def test_failed_fun_review_records_failure_and_stays_at_station_ten(tmp_path):
    ticket = make_ticket("fun-fail", station=Station.FUN_REVIEW)
    ticket.payload["merge_to_main"] = True
    line, queue, _ = make_line(tmp_path, [ticket], {Station.FUN_REVIEW: failing})

    outcome = line.step(NOW)

    saved = queue.get("fun-fail")
    assert outcome.kind == "failed_attempt"
    assert saved.station is Station.FUN_REVIEW
    assert saved.failures[-1].check == "quality"


def test_non_merge_ticket_still_goes_from_prompt_snapshot_to_live_playtest(tmp_path):
    ticket = make_ticket("no-merge", station=Station.PROMPT_SNAPSHOT)
    line, queue, _ = make_line(tmp_path, [ticket], {Station.PROMPT_SNAPSHOT: passing})

    assert line.step(NOW).kind == "advanced"
    assert queue.get("no-merge").station is Station.LIVE_PLAYTEST


def test_live_playtest_infrastructure_failure_retries(tmp_path):
    ticket = make_ticket("playtest-retry", station=Station.LIVE_PLAYTEST)
    line, queue, _ = make_line(
        tmp_path,
        [ticket],
        {Station.LIVE_PLAYTEST: lambda ticket, now: StationResult(False, "playtest", "runner failed")},
    )

    assert line.step(NOW).kind == "failed_attempt"
    assert queue.get("playtest-retry").station is Station.LIVE_PLAYTEST
    assert queue.get("playtest-retry").attempts == 1


def test_unsupported_repair_is_parked_without_failure_or_wiring_retry(tmp_path):
    ticket = make_ticket("unsupported", station=Station.WIRING)

    def planner_result(ticket, now):
        ticket.payload["unsupported_reroute"] = {
            "reroute": "station_code",
            "reason": "Reroute: provider wiring defect is outside the story-fix menu.",
            "since": now.isoformat(),
        }
        return StationResult(False, "wiring", "", tokens=9)

    line, queue, _ = make_line(tmp_path, [ticket], {Station.WIRING: planner_result})

    outcome = line.step(NOW)

    saved = queue.get("unsupported")
    assert outcome.kind == "owner_wait"
    assert outcome.detail == "station_code"
    assert saved.status is Status.SET_ASIDE
    assert saved.attempts == 0
    assert saved.failures == []
    assert saved.payload["reroute"] == "station_code"
    assert saved.payload["reroute_reason"].startswith("Reroute:")
    assert saved.payload["owner_wait"]["reply"] is None
    assert line.step(NOW).kind == "idle"


def test_triage_pass_opens_followups_and_passes_parent(tmp_path):
    ticket = make_ticket("triage-parent", station=Station.TRIAGE)
    routing = {
        "routed": [{"key": "a", "scene": "1A", "class": "story_data", "rule": "R2"}],
        "escalations": [],
        "turns": [{"key": "a", "scene": "1A"}],
    }
    line, queue, _ = make_line(
        tmp_path,
        [ticket],
        {Station.TRIAGE: lambda ticket, now: StationResult(True, "triage", "ok", routing=routing)},
    )

    outcome = line.step(NOW)

    assert outcome.kind == "triaged"
    assert outcome.detail == "triage-parent-1A-story_data"
    assert queue.get("triage-parent").status is Status.PASSED
    assert queue.get("triage-parent-1A-story_data").station is Station.DIAGNOSE
    assert all(saved.station is not Station.DELIVER for saved in queue.all())


def test_triage_pass_without_routing_passes_without_followups(tmp_path):
    ticket = make_ticket("triage-empty", station=Station.TRIAGE)
    line, queue, _ = make_line(
        tmp_path,
        [ticket],
        {Station.TRIAGE: lambda ticket, now: StationResult(True, "triage", "nothing")},
    )

    outcome = line.step(NOW)

    assert outcome == outcome.__class__("triaged", "triage-empty", "")
    assert queue.get("triage-empty").status is Status.PASSED
    assert len(queue.all()) == 1


def test_triage_failure_retries(tmp_path):
    ticket = make_ticket("triage-retry", station=Station.TRIAGE)
    line, queue, _ = make_line(
        tmp_path,
        [ticket],
        {Station.TRIAGE: lambda ticket, now: StationResult(False, "triage", "still unclear")},
    )

    assert line.step(NOW).kind == "failed_attempt"
    assert queue.get("triage-retry").station is Station.TRIAGE
    assert queue.get("triage-retry").attempts == 1


def test_failure_retries_and_increments_attempts(tmp_path):
    ticket = make_ticket("retry")
    calls = 0

    def handler(ticket, now):
        nonlocal calls
        calls += 1
        return failing(ticket, now) if calls < 3 else passing(ticket, now)

    line, queue, _ = make_line(tmp_path, [ticket], {Station.ACT_CONTRACTS: handler})

    assert line.step(NOW).kind == "failed_attempt"
    assert queue.get("retry").attempts == 1
    assert line.step(NOW).kind == "failed_attempt"
    assert queue.get("retry").attempts == 2
    assert line.step(NOW).kind == "advanced"
    assert queue.get("retry").attempts == 0


def test_full_ladder_sets_ticket_aside_and_other_ticket_continues(tmp_path):
    first = make_ticket("first")
    second = make_ticket("second", created_at=NOW + timedelta(seconds=1))
    line, queue, _ = make_line(tmp_path, [first, second], {Station.ACT_CONTRACTS: failing}, set_aside_s=100)

    outcomes = [line.step(NOW) for _ in range(10)]

    assert [outcome.kind for outcome in outcomes[:9]] == ["failed_attempt"] * 9
    assert outcomes[9].ticket_id == "second"
    assert queue.get("first").status is Status.SET_ASIDE
    assert queue.get("first").ladder_rung is LadderRung.SET_ASIDE
    assert queue.get("second").attempts == 1


def test_set_aside_ticket_returns_after_deadline(tmp_path):
    ticket = make_ticket("later")
    ticket.ladder_rung = LadderRung.SET_ASIDE
    line, queue, _ = make_line(tmp_path, [ticket], {station: passing for station in Station}, set_aside_s=10)

    assert line.step(NOW).kind == "advanced"
    ticket = queue.get("later")
    ticket.ladder_rung = LadderRung.SET_ASIDE
    ticket.status = Status.SET_ASIDE
    ticket.return_after = (NOW + timedelta(seconds=10)).isoformat()
    queue.save(ticket)
    assert line.step(NOW + timedelta(seconds=9)).kind == "idle"
    assert line.step(NOW + timedelta(seconds=10)).kind == "advanced"


def test_limit_sleep_only_blocks_that_provider_lane(tmp_path):
    first = make_ticket("alpha", created_at=NOW)
    second = make_ticket("beta", created_at=NOW + timedelta(seconds=1))
    second.payload["provider"] = "beta"

    def handler(ticket, now):
        if ticket.id == "alpha":
            raise LimitSleep("alpha", NOW + timedelta(seconds=30))
        return passing(ticket, now)

    line, queue, state = make_line(tmp_path, [first, second], {Station.ACT_CONTRACTS: handler})

    assert line.step(NOW).kind == "slept"
    assert line.step(NOW).ticket_id == "beta"
    assert state.lanes["alpha"] == (NOW + timedelta(seconds=30)).isoformat()
    assert queue.get("alpha").status is Status.SLEEPING


def test_limit_sleep_does_not_change_attempts_or_failures(tmp_path):
    ticket = make_ticket("limited")
    ticket.attempts = 2

    def handler(ticket, now):
        raise LimitSleep("alpha", NOW + timedelta(seconds=5))

    line, queue, _ = make_line(
        tmp_path,
        [ticket],
        {Station.ACT_CONTRACTS: handler},
    )

    assert line.step(NOW).kind == "slept"
    saved = queue.get("limited")
    assert saved.attempts == 2
    assert saved.failures == []


def test_limit_sleep_without_resume_uses_probe_interval(tmp_path):
    ticket = make_ticket("probe")
    line, _, state = make_line(
        tmp_path,
        [ticket],
        {Station.ACT_CONTRACTS: lambda ticket, now: (_ for _ in ()).throw(LimitSleep("alpha", None))},
        probe_s=17,
    )

    assert line.step(NOW).kind == "slept"
    assert state.lanes["alpha"] == (NOW + timedelta(seconds=17)).isoformat()


def test_sleeping_lane_resumes_at_deadline(tmp_path):
    ticket = make_ticket("resume")
    line, _, state = make_line(tmp_path, [ticket], {Station.ACT_CONTRACTS: passing})
    state.sleep_lane("alpha", NOW + timedelta(seconds=5))

    assert line.step(NOW).kind == "idle"
    assert line.step(NOW + timedelta(seconds=5)).kind == "advanced"
    assert "alpha" not in state.lanes
    assert "alpha" not in state.limited_since


def test_breaker_halts_next_step_and_survives_reload(tmp_path):
    ticket = make_ticket("breaker")
    line, queue, state = make_line(
        tmp_path, [ticket], {Station.ACT_CONTRACTS: passing}, check_breakers=lambda now: ["budget", "quota"]
    )

    assert line.step(NOW).kind == "advanced"
    assert queue.get("breaker").status is Status.QUEUED
    reloaded = FactoryState.load(tmp_path / "state.json")
    reloaded_line = FactoryLine(
        queue=queue,
        state=reloaded,
        handlers={Station.CONTRACT_REFRESH: passing},
        provider_for=lambda ticket: "alpha",
        check_breakers=lambda now: [],
    )
    assert reloaded_line.step(NOW).kind == "halted"
    assert reloaded.breaker_reason() == "budget; quota"


def test_unknown_handler_exception_propagates(tmp_path):
    ticket = make_ticket("crash")

    def crash(ticket, now):
        raise RuntimeError("provider crashed")

    line, queue, _ = make_line(tmp_path, [ticket], {Station.ACT_CONTRACTS: crash})

    with pytest.raises(RuntimeError, match="provider crashed"):
        line.step(NOW)
    assert queue.get("crash").status is Status.RUNNING


def test_missing_handler_names_station(tmp_path):
    ticket = make_ticket("missing", station=Station.WIRING)
    line, _, _ = make_line(tmp_path, [ticket], {})

    with pytest.raises(ValueError, match="WIRING"):
        line.step(NOW)


def test_run_sleeps_until_wake_and_stops_when_passed(tmp_path):
    ticket = make_ticket("run", station=Station.DELIVER)
    calls = 0
    current = [NOW]
    sleeps = []

    def handler(ticket, now):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LimitSleep("alpha", NOW + timedelta(seconds=5))
        return passing(ticket, now)

    def sleep(seconds):
        sleeps.append(seconds)
        current[0] += timedelta(seconds=seconds)

    line, queue, _ = make_line(tmp_path, [ticket], {Station.DELIVER: handler})
    outcomes = line.run(clock=lambda: current[0], sleep=sleep)

    assert [outcome.kind for outcome in outcomes] == ["slept", "idle", "delivered"]
    assert sleeps == [5]
    assert queue.get("run").status is Status.PASSED


def test_run_stops_on_halt(tmp_path):
    ticket = make_ticket("stop")
    line, _, _ = make_line(tmp_path, [ticket], {Station.ACT_CONTRACTS: passing}, check_breakers=lambda now: ["tripped"])

    outcomes = line.run(clock=lambda: NOW, sleep=lambda seconds: pytest.fail("should not sleep"))

    assert [outcome.kind for outcome in outcomes] == ["advanced", "halted"]


def test_tokens_accumulate(tmp_path):
    ticket = make_ticket("tokens")
    line, queue, _ = make_line(
        tmp_path,
        [ticket],
        {
            Station.ACT_CONTRACTS: lambda ticket, now: StationResult(True, "one", "ok", tokens=7),
            Station.CONTRACT_REFRESH: lambda ticket, now: StationResult(True, "two", "ok", tokens=3),
        },
    )

    line.step(NOW)
    line.step(NOW)

    assert queue.get("tokens").tokens_used == 10


def test_provider_for_none_sleeps_error_provider_lane(tmp_path):
    ticket = make_ticket("script")

    def handler(ticket, now):
        raise LimitSleep("unused", NOW + timedelta(seconds=5))

    line, _, state = make_line(
        tmp_path,
        [ticket],
        {Station.ACT_CONTRACTS: handler},
        provider_for=lambda ticket: None,
    )

    assert line.step(NOW).kind == "slept"
    assert state.lanes == {"unused": (NOW + timedelta(seconds=5)).isoformat()}
    assert state.limited_since == {"unused": (NOW + timedelta(seconds=5)).isoformat()}


def test_run_stops_when_no_ticket_can_progress(tmp_path):
    ticket = make_ticket("running")
    ticket.status = Status.RUNNING
    line, _, _ = make_line(tmp_path, [ticket], {Station.ACT_CONTRACTS: passing})

    outcomes = line.run(clock=lambda: NOW, sleep=lambda seconds: pytest.fail("should not sleep"))

    assert len(outcomes) == 1
    assert outcomes[0].kind == "idle"


def test_initial_breaker_returns_halted_without_running_ticket(tmp_path):
    ticket = make_ticket("already-halted")
    line, queue, state = make_line(tmp_path, [ticket], {Station.ACT_CONTRACTS: passing})
    state.trip_breaker("manual", NOW)

    assert line.step(NOW).kind == "halted"
    assert queue.get("already-halted").status is Status.QUEUED


def test_provider_overdue_uses_first_limit_through_repeated_probes(tmp_path):
    ticket = make_ticket("overdue")
    ticket.payload["provider"] = "codex"
    reset = NOW
    calls = 0
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    state = FactoryState.load(tmp_path / "state.json")
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    caps = Caps(100.0, {}, [], 3600, 100.0)
    config = BreakerConfig(provider_overdue_s=86400)

    def handler(ticket, now):
        nonlocal calls
        calls += 1
        raise LimitSleep("codex", reset if calls == 1 else None)

    def breaker_reasons(now):
        return [
            trip.reason
            for trip in check_breakers(
                queue=queue,
                state=state,
                ledger=ledger,
                caps=caps,
                config=config,
                now=now,
            )
        ]

    line = FactoryLine(
        queue=queue,
        state=state,
        handlers={Station.ACT_CONTRACTS: handler},
        provider_for=lambda ticket: ticket.payload.get("provider"),
        check_breakers=breaker_reasons,
        probe_s=1800,
    )

    assert line.step(reset).kind == "slept"
    for offset in range(30 * 60, 24 * 3600, 30 * 60):
        assert line.step(reset + timedelta(seconds=offset)).kind == "slept"
        assert not state.is_tripped()
    assert line.step(reset + timedelta(hours=24)).kind == "slept"
    assert state.is_tripped()
    assert "provider codex" in state.breaker_reason()
    assert reset.isoformat() in state.breaker_reason()


def test_weekly_reset_limit_does_not_trip_before_reset(tmp_path):
    ticket = make_ticket("weekly")
    reset = NOW + timedelta(days=6)
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    state = FactoryState.load(tmp_path / "state.json")
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    caps = Caps(100.0, {}, [], 3600, 100.0)
    config = BreakerConfig(provider_overdue_s=86400)
    line = FactoryLine(
        queue=queue,
        state=state,
        handlers={Station.ACT_CONTRACTS: lambda ticket, now: (_ for _ in ()).throw(LimitSleep("codex", reset))},
        provider_for=lambda ticket: ticket.payload.get("provider"),
        check_breakers=lambda now: [],
    )

    assert line.step(NOW).kind == "slept"
    for hour in range(1, 6 * 24):
        now = NOW + timedelta(hours=hour)
        trips = check_breakers(
            queue=queue,
            state=state,
            ledger=ledger,
            caps=caps,
            config=config,
            now=now,
        )
        assert not any(trip.name == "provider_overdue" for trip in trips)
