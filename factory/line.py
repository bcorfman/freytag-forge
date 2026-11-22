"""Deterministic orchestration for the factory's persisted ticket queue."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from factory.breakers import Notifier
from factory.followups import open_followups
from factory.guard import LimitSleep
from factory.lessons import record_lessons
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
MAX_OWNER_NOTICE_ATTEMPTS = 3
LOGGER = logging.getLogger(__name__)


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
        notifier: Notifier | None = None,
        max_attempts: int = 3,
        set_aside_s: int = 21600,
        probe_s: int = 1800,
    ) -> None:
        self.queue = queue
        self.state = state
        self.handlers = handlers
        self.provider_for = provider_for
        self.check_breakers = check_breakers
        self.notifier = notifier
        self.max_attempts = max_attempts
        self.set_aside_s = set_aside_s
        self.probe_s = probe_s

    def _next_ready(self, now: datetime) -> tuple[Ticket, str | None] | None:
        for ticket in self.queue.all():
            owner_wait = ticket.payload.get("owner_wait")
            if isinstance(owner_wait, dict) and owner_wait.get("reply") is None:
                continue
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

    @staticmethod
    def _clip(value: object) -> str:
        return str(value)[:160]

    @staticmethod
    def _notice_attempts(ticket: Ticket) -> int:
        notice = ticket.payload.get("owner_notice")
        if not isinstance(notice, dict):
            return 0
        attempts = notice.get("attempts")
        if not isinstance(attempts, int) or isinstance(attempts, bool):
            return 0
        return max(0, attempts)

    def _owner_notice_body(self, ticket: Ticket) -> str | None:
        history = ticket.payload.get("fun_history")
        if not isinstance(history, list) or len(history) < 2:
            return None

        lines: list[str] = []
        for number, entry in enumerate(history[:2], start=1):
            if not isinstance(entry, dict):
                entry = {}
            plan = entry.get("plan")
            if not isinstance(plan, dict):
                plan = {}
            fix_kind = plan.get("kind") if isinstance(plan.get("kind"), str) else "unknown"
            reason = plan.get("reason") if isinstance(plan.get("reason"), str) else "see ticket"
            if reason.startswith("Precedent: "):
                reason = reason[len("Precedent: ") :]
            failed_checks = entry.get("failed_checks")
            if isinstance(failed_checks, list):
                failed = ", ".join(str(check) for check in failed_checks if isinstance(check, str)) or "none"
            else:
                failed = "none"
            reasons = entry.get("reasons") if isinstance(entry.get("reasons"), str) else ""
            lines.extend(
                [
                    f"Fix {number} (blocked): {self._clip(fix_kind)}: {self._clip(reason)}",
                    f"  Failed: {self._clip(failed)}. Reviewer: {self._clip(reasons)}",
                ]
            )

        stuck_summary = ticket.payload.get("stuck_summary")
        if not isinstance(stuck_summary, str) or not stuck_summary:
            stuck_summary = "see ticket"
        advice = history[1].get("fun_advice") if isinstance(history[1], dict) else ""
        if not isinstance(advice, str):
            advice = ""
        return "\n".join(
            [
                f"Scene {self._clip(ticket.scene)}, ticket {self._clip(ticket.id)}.",
                f"Stuck: {self._clip(stuck_summary)}",
                *lines,
                f"Last advice: {self._clip(advice)}",
                "Nothing was merged. The ticket is parked and will not retry until you answer.",
                "You may: (1) merge fix 1 or 2 anyway, (2) let it retry with a note for the planner, "
                "(3) drop this scene's ticket.",
            ]
        )

    def _send_owner_notice(self, ticket: Ticket, now: datetime) -> None:
        if self.notifier is None:
            return
        notice = ticket.payload.get("owner_notice")
        if isinstance(notice, dict) and notice.get("sent_at") is not None:
            return
        attempts = self._notice_attempts(ticket)
        if attempts >= MAX_OWNER_NOTICE_ATTEMPTS:
            return
        body = self._owner_notice_body(ticket)
        if body is None:
            return
        attempt = attempts + 1
        subject = f"factory: scene {ticket.scene} needs your call (fun review blocked twice, {ticket.id})"
        try:
            self.notifier.notify(subject, body)
        except Exception as error:
            LOGGER.exception("owner notification failed for ticket %s", ticket.id)
            ticket.payload["owner_notice"] = {
                "sent_at": None,
                "attempts": attempt,
                "error": str(error)[:200],
            }
        else:
            ticket.payload["owner_notice"] = {
                "sent_at": now.astimezone(UTC).isoformat(),
                "attempts": attempt,
            }
        self.queue.save(ticket)

    def _escalate_fun_impasse(self, ticket: Ticket) -> None:
        history = ticket.payload.get("fun_history")
        if not isinstance(history, list) or len(history) < 2:
            return
        owner_wait = ticket.payload.get("owner_wait")
        if not isinstance(owner_wait, dict) or not isinstance(owner_wait.get("since"), str):
            return
        now = _parse_datetime(owner_wait["since"])
        self._send_owner_notice(ticket, now)

    def _retry_owner_notifications(self, now: datetime) -> None:
        if self.notifier is None:
            return
        for ticket in self.queue.all():
            owner_wait = ticket.payload.get("owner_wait")
            if (
                not isinstance(owner_wait, dict)
                or owner_wait.get("reason") != "fun_review_blocked_twice"
                or owner_wait.get("reply") is not None
            ):
                continue
            notice = ticket.payload.get("owner_notice")
            if isinstance(notice, dict) and notice.get("sent_at") is not None:
                continue
            if self._notice_attempts(ticket) >= MAX_OWNER_NOTICE_ATTEMPTS:
                continue
            self._send_owner_notice(ticket, now)

    def _check_breakers(self, now: datetime) -> None:
        reasons = self.check_breakers(now)
        if reasons:
            self.state.trip_breaker("; ".join(reasons), now)
            self.state.save()

    def _record_fun_lessons(self, ticket: Ticket, outcome: str) -> None:
        history = ticket.payload.get("fun_history")
        if not isinstance(history, list) or not history:
            return
        try:
            record_lessons(ticket, outcome)
        except Exception:
            return
        self.queue.save(ticket)

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
                passed_ticket = self.queue.record_pass(ticket.id, now)
                self._record_fun_lessons(passed_ticket, "delivered")
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
                        failed_ticket = self.queue.record_failure(
                            ticket.id,
                            result.check,
                            result.output,
                            now,
                            max_attempts=1,
                            set_aside_s=self.set_aside_s,
                        )
                        self._record_fun_lessons(failed_ticket, "fun_exhausted")
                        failed_ticket.payload["owner_wait"] = {
                            "reason": "fun_review_blocked_twice",
                            "since": now.astimezone(UTC).isoformat(),
                            "reply": None,
                        }
                        self.queue.save(failed_ticket)
                        self._escalate_fun_impasse(failed_ticket)
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
                    self._record_fun_lessons(updated, "fun_exhausted")
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
            owner_wait = ticket.payload.get("owner_wait")
            if isinstance(owner_wait, dict) and owner_wait.get("reply") is None:
                continue
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
            self._retry_owner_notifications(now)
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
