"""Deterministic orchestration for the factory's persisted ticket queue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from factory.followups import open_followups
from factory.guard import LimitSleep
from factory.state import FactoryState
from factory.tickets import LadderRung, Station, Status, Ticket, TicketQueue


@dataclass
class StationResult:
    """The result of one model-backed station check."""

    passed: bool
    check: str
    output: str
    tokens: int = 0
    turns: list[dict] | None = None
    routing: dict | None = None
    payload_updates: dict | None = None


StationHandler = Callable[[Ticket, datetime], StationResult]
MAX_PROBE_ROUNDS = 3
MAX_FUN_ROUNDS = 2


@dataclass
class StepOutcome:
    """The observable result of one line step."""

    kind: str
    ticket_id: str | None
    detail: str = ""


def _parse_datetime(value: str) -> datetime:
    """Parse a persisted ISO timestamp."""

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class FactoryLine:
    """Drive persisted tickets through fixed stations and injected handlers."""

    def __init__(
        self,
        *,
        queue: TicketQueue,
        state: FactoryState,
        handlers: dict[Station, StationHandler],
        provider_for: Callable[[Ticket], str | None],
        check_breakers: Callable[[datetime], list[str]],
        max_attempts: int = 3,
        set_aside_s: int = 21600,
        probe_s: int = 1800,
    ) -> None:
        self.queue = queue
        self.state = state
        self.handlers = handlers
        self.provider_for = provider_for
        self.check_breakers = check_breakers
        self.max_attempts = max_attempts
        self.set_aside_s = set_aside_s
        self.probe_s = probe_s

    def _next_ready(self, now: datetime) -> tuple[Ticket, str | None] | None:
        for ticket in self.queue.all():
            if ticket.status is Status.QUEUED:
                ready = True
            elif ticket.status is Status.SLEEPING and ticket.sleep_until is not None:
                ready = _parse_datetime(ticket.sleep_until) <= now
            elif ticket.status is Status.SET_ASIDE and ticket.return_after is not None:
                ready = _parse_datetime(ticket.return_after) <= now
            else:
                ready = False
            if not ready:
                continue

            provider = self.provider_for(ticket)
            if provider is not None and not self.state.lane_ready(provider, now):
                continue
            return ticket, provider
        return None

    def _check_breakers(self, now: datetime) -> None:
        reasons = self.check_breakers(now)
        if reasons:
            self.state.trip_breaker("; ".join(reasons), now)
            self.state.save()

    def step(self, now: datetime) -> StepOutcome:
        if self.state.is_tripped():
            return StepOutcome("halted", None)

        selected = self._next_ready(now)
        if selected is None:
            return StepOutcome("idle", None)

        ticket, provider = selected
        self.queue.mark_running(ticket.id, now)
        handler = self.handlers.get(ticket.station)
        if handler is None:
            raise ValueError(f"missing handler for station {ticket.station.name}")

        try:
            result = handler(ticket, now)
        except LimitSleep as error:
            resume_at = error.resume_at or now + timedelta(seconds=self.probe_s)
            lane = provider if provider is not None else error.provider
            self.state.sleep_lane(lane, resume_at, since=error.resume_at or now)
            self.queue.record_limit_hit(ticket.id, error.provider, resume_at, now)
            self._check_breakers(now)
            return StepOutcome("slept", ticket.id)

        if provider is not None:
            self.state.lane_succeeded(provider)
        self.queue.record_tokens(ticket.id, result.tokens)
        if result.payload_updates:
            updated = self.queue.get(ticket.id)
            updated.payload.update(result.payload_updates)
            self.queue.save(updated)
        if result.passed:
            merged_payload = {**ticket.payload, **(result.payload_updates or {})}
            merge_to_main = merged_payload.get("merge_to_main") is True
            if ticket.station is Station.LIVE_PLAYTEST and merge_to_main:
                self.queue.record_pass(ticket.id, now)
                outcome = StepOutcome("delivered", ticket.id)
            elif ticket.station is Station.TRIAGE:
                opened = open_followups(self.queue, ticket, result.routing, now) if result.routing is not None else []
                self.queue.record_pass(ticket.id, now)
                outcome = StepOutcome("triaged", ticket.id, ",".join(item.id for item in opened))
            elif ticket.station is Station.DELIVER and not merge_to_main:
                self.queue.record_pass(ticket.id, now)
                outcome = StepOutcome("delivered", ticket.id)
            else:
                updated = self.queue.get(ticket.id)
                if ticket.station is Station.PROBE:
                    updated.payload.pop("probe_feedback", None)
                    updated.payload.pop("feedback_plan", None)
                    updated.payload.pop("fun_feedback", None)
                if ticket.station is Station.FUN_REVIEW:
                    updated.payload.pop("fun_feedback", None)
                    updated.payload.pop("feedback_plan", None)
                if ticket.station is Station.DIAGNOSE:
                    updated.station = Station.WIRING
                elif ticket.station is Station.PROMPT_SNAPSHOT:
                    updated.station = Station.PROBE if merge_to_main else Station.LIVE_PLAYTEST
                elif ticket.station is Station.LIVE_PLAYTEST:
                    updated.station = Station.FUN_REVIEW if merge_to_main else Station.DELIVER
                elif ticket.station is Station.FUN_REVIEW and merge_to_main:
                    updated.station = Station.DELIVER
                elif ticket.station is Station.DELIVER and merge_to_main:
                    updated.station = Station.LIVE_PLAYTEST
                elif ticket.station is Station.PROBE:
                    updated.station = Station.FUN_REVIEW
                else:
                    updated.station = Station(ticket.station + 1)
                updated.status = Status.QUEUED
                updated.attempts = 0
                updated.ladder_rung = LadderRung.LUNA_RETRY
                updated.provider = None
                updated.sleep_until = None
                updated.return_after = None
                self.queue.save(updated)
                outcome = StepOutcome("advanced", ticket.id)
        else:
            probe_update = result.payload_updates.get("probe") if isinstance(result.payload_updates, dict) else None
            probe_verdict = probe_update.get("verdict") if isinstance(probe_update, dict) else None
            if ticket.station is Station.PROBE and probe_verdict in {"reject", "inconclusive"}:
                probe_rounds = ticket.payload.get("probe_rounds", 0)
                if not isinstance(probe_rounds, int) or isinstance(probe_rounds, bool):
                    probe_rounds = 0
                next_probe_round = probe_rounds + 1
                if next_probe_round < MAX_PROBE_ROUNDS:
                    updated = self.queue.get(ticket.id)
                    updated.station = Station.WIRING
                    updated.status = Status.QUEUED
                    updated.attempts = 0
                    updated.ladder_rung = LadderRung.LUNA_RETRY
                    updated.provider = None
                    updated.sleep_until = None
                    updated.return_after = None
                    updated.payload["probe_rounds"] = next_probe_round
                    updated.payload["feedback_plan"] = ticket.payload.get("plan")
                    feedback = probe_update.get("feedback")
                    probe_feedback = feedback if isinstance(feedback, str) else result.output
                    history = updated.payload.get("fun_history")
                    if isinstance(history, list) and history:
                        last_entry = history[-1] if isinstance(history[-1], dict) else {}
                        reasons = last_entry.get("reasons") if isinstance(last_entry.get("reasons"), str) else ""
                        fun_advice = (
                            last_entry.get("fun_advice") if isinstance(last_entry.get("fun_advice"), str) else ""
                        )
                        probe_feedback += f"\n\nEarlier fun review advice (still applies):\nReasons: {reasons}"
                        if fun_advice:
                            probe_feedback += f"\nfun_advice: {fun_advice}"
                    updated.payload["probe_feedback"] = probe_feedback
                    updated.payload.pop("plan", None)
                    updated.payload.pop("fun_feedback", None)
                    self.queue.save(updated)
                    outcome = StepOutcome("probe_rejected", ticket.id)
                else:
                    updated = self.queue.get(ticket.id)
                    updated.ladder_rung = LadderRung.OPUS_REFRESH
                    self.queue.save(updated)
                    self.queue.record_failure(
                        ticket.id,
                        result.check,
                        result.output,
                        now,
                        max_attempts=1,
                        set_aside_s=self.set_aside_s,
                    )
                    outcome = StepOutcome("failed_attempt", ticket.id)
            else:
                fun_update = (
                    result.payload_updates.get("fun_review") if isinstance(result.payload_updates, dict) else None
                )
                fun_verdict = fun_update.get("verdict") if isinstance(fun_update, dict) else None
                if ticket.station is Station.FUN_REVIEW and fun_verdict == "block":
                    fun_rounds = ticket.payload.get("fun_rounds", 0)
                    if not isinstance(fun_rounds, int) or isinstance(fun_rounds, bool):
                        fun_rounds = 0
                    next_fun_round = fun_rounds + 1
                    updated = self.queue.get(ticket.id)
                    blocked_plan = ticket.payload.get("plan")
                    if not isinstance(blocked_plan, dict):
                        blocked_plan = fun_update.get("plan")
                    if not isinstance(blocked_plan, dict):
                        blocked_plan = {}
                    reasons = fun_update.get("reasons")
                    reasons = reasons if isinstance(reasons, str) else ""
                    fun_advice = fun_update.get("fun_advice")
                    fun_advice = fun_advice if isinstance(fun_advice, str) else ""
                    failed_checks = fun_update.get("failed_checks")
                    if not isinstance(failed_checks, list):
                        failed_checks = []
                    failed_checks = [key for key in failed_checks if isinstance(key, str)]
                    history_entry = {
                        "plan": blocked_plan,
                        "reasons": reasons,
                        "fun_advice": fun_advice,
                        "failed_checks": failed_checks,
                    }
                    history = updated.payload.get("fun_history")
                    if not isinstance(history, list):
                        history = []
                    last_entry = history[-1] if history and isinstance(history[-1], dict) else None
                    history_keys = ("plan", "reasons", "fun_advice", "failed_checks")
                    if last_entry is None or any(last_entry.get(key) != history_entry[key] for key in history_keys):
                        history.append(history_entry)
                    updated.payload["fun_history"] = history
                    if next_fun_round < MAX_FUN_ROUNDS:
                        updated.station = Station.WIRING
                        updated.status = Status.QUEUED
                        updated.attempts = 0
                        updated.ladder_rung = LadderRung.LUNA_RETRY
                        updated.provider = None
                        updated.sleep_until = None
                        updated.return_after = None
                        updated.payload["fun_rounds"] = next_fun_round
                        updated.payload["feedback_plan"] = blocked_plan
                        feedback_lines = [
                            (
                                "Failed checks: none (blocked by the rule against only moving words)"
                                if not failed_checks
                                else "Failed checks: " + ", ".join(failed_checks)
                            ),
                            "Reasons: " + reasons,
                        ]
                        if fun_advice:
                            feedback_lines.append("fun_advice: " + fun_advice)
                        updated.payload["fun_feedback"] = "\n".join(feedback_lines)
                        updated.payload.pop("plan", None)
                        updated.payload.pop("probe_feedback", None)
                        updated.payload.pop("fun_review", None)
                        self.queue.save(updated)
                        outcome = StepOutcome("fun_blocked", ticket.id)
                    else:
                        updated.payload["fun_rounds"] = next_fun_round
                        updated.ladder_rung = LadderRung.OPUS_REFRESH
                        self.queue.save(updated)
                        self.queue.record_failure(
                            ticket.id,
                            result.check,
                            result.output,
                            now,
                            max_attempts=1,
                            set_aside_s=self.set_aside_s,
                        )
                        outcome = StepOutcome("failed_attempt", ticket.id)
                elif ticket.station is Station.LIVE_PLAYTEST and isinstance(result.turns, list) and result.turns:
                    updated = self.queue.get(ticket.id)
                    updated.station = Station.TRIAGE
                    updated.status = Status.QUEUED
                    updated.attempts = 0
                    updated.ladder_rung = LadderRung.LUNA_RETRY
                    updated.provider = None
                    updated.sleep_until = None
                    updated.return_after = None
                    updated.payload["turns"] = result.turns
                    self.queue.save(updated)
                    outcome = StepOutcome("to_triage", ticket.id)
                else:
                    self.queue.record_failure(
                        ticket.id,
                        result.check,
                        result.output,
                        now,
                        max_attempts=self.max_attempts,
                        set_aside_s=self.set_aside_s,
                    )
                    outcome = StepOutcome("failed_attempt", ticket.id)

        self._check_breakers(now)
        return outcome

    def _all_passed(self) -> bool:
        tickets = self.queue.all()
        return not tickets or all(ticket.status is Status.PASSED for ticket in tickets)

    def _next_wake(self, now: datetime) -> datetime | None:
        wake_times: list[datetime] = []
        for ticket in self.queue.all():
            if ticket.status is Status.SLEEPING and ticket.sleep_until is not None:
                wake_times.append(_parse_datetime(ticket.sleep_until))
            elif ticket.status is Status.SET_ASIDE and ticket.return_after is not None:
                wake_times.append(_parse_datetime(ticket.return_after))
        wake_times.extend(_parse_datetime(until) for until in self.state.lanes.values())
        future = [wake for wake in wake_times if wake > now]
        return min(future) if future else None

    def run(
        self,
        *,
        clock: Callable[[], datetime],
        sleep: Callable[[float], None],
        max_steps: int = 10000,
    ) -> list[StepOutcome]:
        outcomes: list[StepOutcome] = []
        for _ in range(max_steps):
            now = clock()
            outcome = self.step(now)
            outcomes.append(outcome)
            if outcome.kind == "halted" or self._all_passed():
                break
            if outcome.kind != "idle":
                continue

            if not self.queue.all():
                break
            wake = self._next_wake(now)
            if wake is None:
                break
            seconds = max(1.0, (wake - now).total_seconds())
            sleep(seconds)
        return outcomes
