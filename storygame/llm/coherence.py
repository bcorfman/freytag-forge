from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Protocol, TypedDict

from storygame.llm.context import NarrationContext

CRITIQUE_DIMENSIONS = ("continuity", "causality", "dialogue_fit")
DEFAULT_WEIGHTS = {"continuity": 0.4, "causality": 0.4, "dialogue_fit": 0.2}
DEFAULT_CRITICAL_FLOORS = {"continuity": 70, "causality": 70}
DEFAULT_THRESHOLD = 80
DEFAULT_MAX_ROUNDS = 10
DEFAULT_MAX_TOKENS_PER_ROLE = {"narrator": 2000, "critics": 2000}
DEFAULT_WALL_CLOCK_TIMEOUT_MS = 1500
DEFAULT_MAX_REVERSAL_ROUNDS = 3
DEFAULT_MAX_VALIDATION_REVISIONS = 10

MOTION_MARKER_PATTERN = re.compile(r"\b(go|head|move|walk|run|sprint|toward|towards|through)\b", re.IGNORECASE)
ROOM_LOCATION_PATTERN = re.compile(r"\bin ([a-z][a-z0-9_ ]+)\b", re.IGNORECASE)
WITH_ITEM_PATTERN = re.compile(r"\bwith the ([a-z][a-z0-9_ -]+)\b", re.IGNORECASE)
CARDINAL_PATTERN = re.compile(r"\b(north|south|east|west|up|down)\b", re.IGNORECASE)


class CritiqueReport(TypedDict):
    critic_id: str
    scores: dict[str, int]
    feedback: str


class JudgeDecision(TypedDict):
    decision_id: str
    status: str
    round_index: int
    threshold: int
    total_score: int
    rubric_components: dict[str, int]
    critical_floors: dict[str, int]
    critic_ids: tuple[str, ...]
    critic_reports: tuple[CritiqueReport, ...]


class CoherenceResult(TypedDict):
    narration: str
    judge_decision: JudgeDecision
    critique_reports: tuple[CritiqueReport, ...]
    telemetry: CoherenceTelemetry
    reversal: ReversalReport
    validator_reports: tuple[ValidationReport, ...]
    validation_revisions: int


class ValidationReport(TypedDict):
    validator_id: str
    passed: bool
    reason_codes: tuple[str, ...]
    details: str


class TokenSpend(TypedDict):
    narrator: int
    critics: int


class CoherenceTelemetry(TypedDict):
    critique_rounds: int
    token_spend: TokenSpend
    elapsed_ms: int
    hard_fail_reason: str


class ReversalDelta(TypedDict):
    preserved: tuple[str, ...]
    modified: tuple[str, ...]
    discarded: tuple[str, ...]


class ReversalReport(TypedDict):
    trigger_reason: str
    seed: tuple[str, ...]
    delta: ReversalDelta
    replan_attempted: bool
    replan_passed: bool


class CritiqueAgent(Protocol):
    critic_id: str

    def critique(self, context: NarrationContext, narration: str) -> CritiqueReport: ...


class CandidateValidator(Protocol):
    validator_id: str

    def validate(self, context: NarrationContext, narration: str) -> ValidationReport: ...


def _normalize(value: str) -> str:
    return "_".join(re.findall(r"[a-z0-9]+", value.lower()))


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _token_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _base_dimension_scores(context: NarrationContext, narration: str) -> dict[str, int]:
    narration_tokens = _token_set(narration)
    goal_tokens = {token for token in _token_set(context.goal) if len(token) >= 5}
    event_tokens: set[str] = set()
    for event in context.recent_events:
        event_tokens.update(token for token in _token_set(str(event.get("message_key", ""))) if len(token) >= 4)
    world_tokens = set()
    world_tokens.update(token for token in _token_set(context.room_name) if len(token) >= 4)
    world_tokens.update(token for token in _token_set(" ".join(context.visible_items)) if len(token) >= 4)
    world_tokens.update(token for token in _token_set(" ".join(context.visible_npcs)) if len(token) >= 4)
    world_tokens.update(token for token in _token_set(" ".join(context.inventory)) if len(token) >= 4)

    overlap_goal = len(goal_tokens.intersection(narration_tokens))
    overlap_event = len(event_tokens.intersection(narration_tokens))
    overlap_world = len(world_tokens.intersection(narration_tokens))

    continuity = 30 + min(30, overlap_goal * 10) + min(25, overlap_event * 5) + min(15, overlap_world * 5)

    causal_markers = ("because", "after", "before", "therefore", "since", "so", "thus")
    causal_hits = sum(1 for marker in causal_markers if marker in narration.lower())
    action_tokens = {token for token in _token_set(context.action) if len(token) >= 3}
    overlap_action = len(action_tokens.intersection(narration_tokens))
    causality = 25 + min(35, causal_hits * 12) + min(20, overlap_action * 5) + min(20, overlap_event * 5)

    dialogue_markers = ("says", "said", "asks", "asked", "replies", "reply", "answer", "tell", "told")
    dialogue_hits = sum(1 for marker in dialogue_markers if marker in narration.lower())
    second_person = "you" in narration_tokens
    in_length_band = 20 <= len(narration.strip()) <= 300
    dialogue_fit = 20 + min(40, dialogue_hits * 10)
    if second_person:
        dialogue_fit += 20
    if in_length_band:
        dialogue_fit += 20

    return {
        "continuity": max(0, min(100, continuity)),
        "causality": max(0, min(100, causality)),
        "dialogue_fit": max(0, min(100, dialogue_fit)),
    }


def _feedback_for_dimension(dimension: str, score: int) -> str:
    if score >= 80:
        return f"{dimension} is strong."
    if score >= 70:
        return f"{dimension} is acceptable but can tighten references."
    if dimension == "continuity":
        return "Reference room facts, recent events, and active goal more explicitly."
    if dimension == "causality":
        return "Use explicit causal links (for example: because/after) tied to the prior event."
    return "Make dialogue more direct and grounded in the player's action."


class _DefaultCritic:
    def __init__(self, critic_id: str, focus_dimension: str) -> None:
        self.critic_id = critic_id
        self._focus_dimension = focus_dimension

    def critique(self, context: NarrationContext, narration: str) -> CritiqueReport:
        scores = _base_dimension_scores(context, narration)
        scores[self._focus_dimension] = min(100, scores[self._focus_dimension] + 5)
        feedback = _feedback_for_dimension(self._focus_dimension, scores[self._focus_dimension])
        return {
            "critic_id": self.critic_id,
            "scores": scores,
            "feedback": feedback,
        }


class _EntityReachabilityValidator:
    validator_id = "entity_reachability"

    def validate(self, context: NarrationContext, narration: str) -> ValidationReport:
        reasons: list[str] = []
        details: list[str] = []
        lower_narration = narration.lower()
        exits = {exit_name.lower() for exit_name in context.exits}
        if MOTION_MARKER_PATTERN.search(lower_narration):
            directions = {match.group(1).lower() for match in CARDINAL_PATTERN.finditer(lower_narration)}
            unreachable = sorted(direction for direction in directions if direction not in exits)
            if unreachable:
                reasons.append("VLD_EXIT_UNREACHABLE")
                details.append(f"unreachable_directions={','.join(unreachable)}")
        return {
            "validator_id": self.validator_id,
            "passed": not reasons,
            "reason_codes": tuple(reasons),
            "details": "; ".join(details),
        }


class _InventoryLocationConsistencyValidator:
    validator_id = "inventory_location_consistency"

    def validate(self, context: NarrationContext, narration: str) -> ValidationReport:
        reasons: list[str] = []
        details: list[str] = []
        lower_narration = narration.lower()
        known_items = {_normalize(item) for item in context.visible_items + context.inventory}

        for match in ROOM_LOCATION_PATTERN.finditer(lower_narration):
            candidate_room = _normalize(match.group(1))
            expected_room = _normalize(context.room_name)
            if candidate_room and candidate_room != expected_room:
                reasons.append("VLD_LOCATION_MISMATCH")
                details.append(f"expected_room={expected_room},found_room={candidate_room}")
                break

        for match in WITH_ITEM_PATTERN.finditer(lower_narration):
            item_name = _normalize(match.group(1))
            if item_name and item_name not in known_items:
                reasons.append("VLD_INVENTORY_ITEM_UNKNOWN")
                details.append(f"unknown_item={item_name}")
                break

        return {
            "validator_id": self.validator_id,
            "passed": not reasons,
            "reason_codes": tuple(reasons),
            "details": "; ".join(details),
        }


class _CommittedStateContradictionValidator:
    validator_id = "committed_state_contradiction"

    def validate(self, context: NarrationContext, narration: str) -> ValidationReport:
        reasons: list[str] = []
        details: list[str] = []
        lower_narration = narration.lower()
        event_messages = [str(event.get("message_key", "")).lower() for event in context.recent_events]

        if event_messages and "nothing happened" in lower_narration:
            reasons.append("VLD_CONTRADICTION_RECENT_EVENTS")
            details.append("narration_claims_nothing_happened")

        event_has_east = any(" east" in message or message.endswith("east") for message in event_messages)
        event_has_west = any(" west" in message or message.endswith("west") for message in event_messages)
        if event_has_east and " west" in lower_narration:
            reasons.append("VLD_CONTRADICTION_DIRECTIONAL")
            details.append("recent_events_point_east_but_narration_points_west")
        if event_has_west and " east" in lower_narration:
            reasons.append("VLD_CONTRADICTION_DIRECTIONAL")
            details.append("recent_events_point_west_but_narration_points_east")

        return {
            "validator_id": self.validator_id,
            "passed": not reasons,
            "reason_codes": tuple(reasons),
            "details": "; ".join(details),
        }


class _BeatTransitionLegalityValidator:
    validator_id = "beat_transition_legality"
    _allowed_by_phase = {
        "exposition": {"hook", "inciting_incident"},
        "rising_action": {
            "progressive_complication",
            "pinch",
            "midpoint_reversal",
            "setback",
        },
        "climax": {"climax"},
        "falling_action": {"resolution", "denouement"},
    }

    def validate(self, context: NarrationContext, narration: str) -> ValidationReport:  # noqa: ARG002
        allowed = self._allowed_by_phase.get(context.phase, set())
        if context.beat in allowed:
            return {
                "validator_id": self.validator_id,
                "passed": True,
                "reason_codes": (),
                "details": "",
            }
        return {
            "validator_id": self.validator_id,
            "passed": False,
            "reason_codes": ("VLD_BEAT_ILLEGAL_FOR_PHASE",),
            "details": f"phase={context.phase},beat={context.beat}",
        }


def _average_dimension_scores(reports: tuple[CritiqueReport, ...]) -> dict[str, int]:
    averages: dict[str, int] = {}
    for dimension in CRITIQUE_DIMENSIONS:
        total = sum(int(report["scores"][dimension]) for report in reports)
        averages[dimension] = int(round(total / len(reports)))
    return averages


def _decision_id(
    round_index: int,
    rubric_components: dict[str, int],
    total_score: int,
    status: str,
    critic_ids: tuple[str, ...],
) -> str:
    payload = {
        "round_index": round_index,
        "rubric_components": rubric_components,
        "total_score": total_score,
        "status": status,
        "critic_ids": critic_ids,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"judge-{round_index}-{digest}"


def judge_critique_round(
    reports: tuple[CritiqueReport, ...] | list[CritiqueReport],
    threshold: int = DEFAULT_THRESHOLD,
    critical_floors: dict[str, int] | None = None,
    round_index: int = 1,
    weights: dict[str, float] | None = None,
) -> JudgeDecision:
    if not reports:
        raise ValueError("judge_critique_round requires at least one critique report.")
    chosen_floors = DEFAULT_CRITICAL_FLOORS if critical_floors is None else critical_floors
    chosen_weights = DEFAULT_WEIGHTS if weights is None else weights
    ordered_reports = tuple(reports)
    component_scores = _average_dimension_scores(ordered_reports)
    weighted_total = sum(component_scores[dim] * chosen_weights[dim] for dim in CRITIQUE_DIMENSIONS)
    total_score = int(round(weighted_total))
    floor_violations = [dim for dim, floor in chosen_floors.items() if component_scores[dim] < floor]
    # Tie-break rule is deterministic: score exactly at threshold still fails on any critical-floor violation.
    status = "accepted" if total_score >= threshold and not floor_violations else "failed"
    critic_ids = tuple(report["critic_id"] for report in ordered_reports)
    return {
        "decision_id": _decision_id(round_index, component_scores, total_score, status, critic_ids),
        "status": status,
        "round_index": round_index,
        "threshold": threshold,
        "total_score": total_score,
        "rubric_components": component_scores,
        "critical_floors": dict(chosen_floors),
        "critic_ids": critic_ids,
        "critic_reports": ordered_reports,
    }


def _revision_directive(reports: tuple[CritiqueReport, ...], decision: JudgeDecision) -> str:
    weakest = sorted(
        decision["rubric_components"].items(),
        key=lambda item: (item[1], item[0]),
    )
    lowest = weakest[0][0]
    feedbacks = [report["feedback"] for report in reports]
    if lowest == "causality":
        focus = "mention causality and dialogue with explicit links to prior events"
    elif lowest == "continuity":
        focus = "mention continuity anchors from room facts and recent events"
    else:
        focus = "mention causality and dialogue while staying tied to the current goal"
    return f"Revision directive: {focus}. Notes: {' | '.join(feedbacks[:2])}"


def _validation_revision_directive(reports: tuple[ValidationReport, ...]) -> str:
    failed = [report for report in reports if not report["passed"]]
    reason_codes: list[str] = []
    for report in failed:
        reason_codes.extend(report["reason_codes"])
    unique_codes = sorted(set(reason_codes))
    return f"Revision directive: fix validation errors. reason_codes={','.join(unique_codes)}"


def _context_with_revision(context: NarrationContext, directive: str) -> NarrationContext:
    existing = list(context.memory_fragments)
    existing.append(directive)
    revised_fragments = tuple(existing[-3:])
    return NarrationContext(
        room_name=context.room_name,
        room_description=context.room_description,
        visible_items=context.visible_items,
        visible_npcs=context.visible_npcs,
        npc_facts=context.npc_facts,
        exits=context.exits,
        inventory=context.inventory,
        recent_events=context.recent_events,
        phase=context.phase,
        tension=context.tension,
        beat=context.beat,
        goal=context.goal,
        action=context.action,
        memory_fragments=revised_fragments,
    )


def _reversal_seed(context: NarrationContext, hard_fail_reason: str, decision_id: str) -> tuple[str, ...]:
    payload = {
        "hard_fail_reason": hard_fail_reason,
        "decision_id": decision_id,
        "room_name": context.room_name,
        "action": context.action,
        "goal": context.goal,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return (
        f"reversal_seed={digest}",
        f"preserve_action={context.action}",
        f"preserve_room={context.room_name}",
    )


def _reversal_delta(context: NarrationContext, hard_fail_reason: str) -> ReversalDelta:
    preserved = (
        f"room={context.room_name}",
        f"action={context.action}",
        f"goal={context.goal}",
        f"inventory={','.join(context.inventory)}",
        f"visible_npcs={','.join(context.visible_npcs)}",
        f"visible_items={','.join(context.visible_items)}",
    )
    modified = (
        "narration_plan",
        "causal_linking",
        "dialogue_grounding",
    )
    discarded = (
        f"failed_branch_reason={hard_fail_reason}",
        "failed_candidate_narration",
    )
    return {
        "preserved": preserved,
        "modified": modified,
        "discarded": discarded,
    }


class CoherenceGate:
    def __init__(
        self,
        critics: tuple[CritiqueAgent, ...],
        validators: tuple[CandidateValidator, ...],
        threshold: int = DEFAULT_THRESHOLD,
        critical_floors: dict[str, int] | None = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        max_tokens_per_role: dict[str, int] | None = None,
        wall_clock_timeout_ms: int = DEFAULT_WALL_CLOCK_TIMEOUT_MS,
        max_reversal_rounds: int = DEFAULT_MAX_REVERSAL_ROUNDS,
        time_source=None,
        max_validation_revisions: int = DEFAULT_MAX_VALIDATION_REVISIONS,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds must be >= 1.")
        if wall_clock_timeout_ms < 1:
            raise ValueError("wall_clock_timeout_ms must be >= 1.")
        if max_reversal_rounds < 1:
            raise ValueError("max_reversal_rounds must be >= 1.")
        if max_validation_revisions < 1:
            raise ValueError("max_validation_revisions must be >= 1.")

        self._critics = critics
        self._validators = validators
        self._threshold = threshold
        self._critical_floors = DEFAULT_CRITICAL_FLOORS if critical_floors is None else dict(critical_floors)
        self._max_rounds = max_rounds
        self._max_tokens_per_role = (
            dict(DEFAULT_MAX_TOKENS_PER_ROLE) if max_tokens_per_role is None else dict(max_tokens_per_role)
        )
        self._wall_clock_timeout_ms = wall_clock_timeout_ms
        self._max_reversal_rounds = max_reversal_rounds
        self._time_source = time.perf_counter if time_source is None else time_source
        self._max_validation_revisions = max_validation_revisions

    def critique_round(self, context: NarrationContext, narration: str) -> tuple[CritiqueReport, ...]:
        return tuple(critic.critique(context, narration) for critic in self._critics)

    def validate_candidate(self, context: NarrationContext, narration: str) -> tuple[ValidationReport, ...]:
        return tuple(validator.validate(context, narration) for validator in self._validators)

    def _validation_failed(self, reports: tuple[ValidationReport, ...]) -> bool:
        return any(not report["passed"] for report in reports)

    def _validation_failure_decision(
        self,
        validation_revisions: int,
        reports: tuple[ValidationReport, ...],
    ) -> JudgeDecision:
        reason_codes: list[str] = []
        for report in reports:
            if report["passed"]:
                continue
            reason_codes.extend(report["reason_codes"])
        ordered_codes = tuple(sorted(set(reason_codes)))
        payload = {
            "validation_revisions": validation_revisions,
            "reason_codes": ordered_codes,
            "threshold": self._threshold,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        return {
            "decision_id": f"judge-vld-{validation_revisions}-{digest}",
            "status": "failed",
            "round_index": 0,
            "threshold": self._threshold,
            "total_score": 0,
            "rubric_components": {dimension: 0 for dimension in CRITIQUE_DIMENSIONS},
            "critical_floors": dict(self._critical_floors),
            "critic_ids": (),
            "critic_reports": (),
        }

    def _run_scoring_pipeline(
        self,
        narrator,
        context: NarrationContext,
        max_rounds: int,
    ) -> tuple[
        str,
        tuple[CritiqueReport, ...],
        tuple[ValidationReport, ...],
        int,
        JudgeDecision,
        CoherenceTelemetry,
    ]:
        current_context = context
        final_reports: tuple[CritiqueReport, ...] = ()
        final_validator_reports: tuple[ValidationReport, ...] = ()
        final_decision: JudgeDecision | None = None
        final_narration = ""

        token_spend: TokenSpend = {"narrator": 0, "critics": 0}
        hard_fail_reason = ""
        start_time = self._time_source()
        elapsed_ms = 0

        validation_revisions = 0
        critique_round_index = 0

        while critique_round_index < max_rounds:
            now = self._time_source()
            elapsed_ms = int(round((now - start_time) * 1000))
            if elapsed_ms > self._wall_clock_timeout_ms:
                hard_fail_reason = "BUDGET_WALL_CLOCK_TIMEOUT"
                break

            narration = narrator.generate(current_context)
            token_spend["narrator"] += _token_count(narration)
            if token_spend["narrator"] > self._max_tokens_per_role["narrator"]:
                final_narration = narration
                hard_fail_reason = "BUDGET_NARRATOR_TOKENS"
                break

            validator_reports = self.validate_candidate(current_context, narration)
            final_validator_reports = validator_reports
            if self._validation_failed(validator_reports):
                validation_revisions += 1
                final_narration = narration
                if validation_revisions >= self._max_validation_revisions:
                    final_decision = self._validation_failure_decision(validation_revisions, validator_reports)
                    break
                current_context = _context_with_revision(
                    current_context,
                    _validation_revision_directive(validator_reports),
                )
                continue

            reports = self.critique_round(current_context, narration)
            critic_token_spend = sum(_token_count(report["feedback"]) for report in reports)
            token_spend["critics"] += critic_token_spend
            if token_spend["critics"] > self._max_tokens_per_role["critics"]:
                final_narration = narration
                final_reports = reports
                hard_fail_reason = "BUDGET_CRITIC_TOKENS"
                break

            critique_round_index += 1
            decision = judge_critique_round(
                reports,
                threshold=self._threshold,
                critical_floors=self._critical_floors,
                round_index=critique_round_index,
            )
            final_narration = narration
            final_reports = reports
            final_decision = decision
            if decision["status"] == "accepted":
                break

            current_context = _context_with_revision(current_context, _revision_directive(reports, decision))

        if final_decision is None:
            if hard_fail_reason == "":
                hard_fail_reason = "BUDGET_MAX_CRITIQUE_ROUNDS"
            final_decision = {
                "decision_id": f"judge-hard-fail-{hard_fail_reason.lower()}",
                "status": "failed",
                "round_index": max_rounds if hard_fail_reason == "BUDGET_MAX_CRITIQUE_ROUNDS" else 0,
                "threshold": self._threshold,
                "total_score": 0,
                "rubric_components": {dimension: 0 for dimension in CRITIQUE_DIMENSIONS},
                "critical_floors": dict(self._critical_floors),
                "critic_ids": tuple(report["critic_id"] for report in final_reports),
                "critic_reports": final_reports,
            }

        now = self._time_source()
        elapsed_ms = int(round((now - start_time) * 1000))
        if (
            hard_fail_reason == ""
            and final_decision["status"] == "failed"
            and final_decision["round_index"] >= max_rounds
        ):
            hard_fail_reason = "BUDGET_MAX_CRITIQUE_ROUNDS"

        telemetry: CoherenceTelemetry = {
            "critique_rounds": final_decision["round_index"],
            "token_spend": token_spend,
            "elapsed_ms": elapsed_ms,
            "hard_fail_reason": hard_fail_reason,
        }

        return (
            final_narration,
            final_reports,
            final_validator_reports,
            validation_revisions,
            final_decision,
            telemetry,
        )

    def generate_with_gate(self, narrator, context: NarrationContext) -> CoherenceResult:
        (
            final_narration,
            final_reports,
            final_validator_reports,
            validation_revisions,
            final_decision,
            telemetry,
        ) = self._run_scoring_pipeline(
            narrator,
            context,
            max_rounds=self._max_rounds,
        )

        reversal: ReversalReport = {
            "trigger_reason": "",
            "seed": (),
            "delta": {"preserved": (), "modified": (), "discarded": ()},
            "replan_attempted": False,
            "replan_passed": False,
        }

        hard_fail_reason = str(telemetry["hard_fail_reason"])
        can_replan = hard_fail_reason in {
            "BUDGET_MAX_CRITIQUE_ROUNDS",
            "BUDGET_NARRATOR_TOKENS",
            "BUDGET_CRITIC_TOKENS",
        }

        if final_decision["status"] == "failed" and can_replan:
            seed = _reversal_seed(context, hard_fail_reason, final_decision["decision_id"])
            delta = _reversal_delta(context, hard_fail_reason)
            reversal = {
                "trigger_reason": hard_fail_reason,
                "seed": seed,
                "delta": delta,
                "replan_attempted": True,
                "replan_passed": False,
            }

            reversal_context = context
            for seed_line in seed:
                reversal_context = _context_with_revision(reversal_context, seed_line)

            (
                replan_narration,
                replan_reports,
                replan_validator_reports,
                replan_validation_revisions,
                replan_decision,
                replan_telemetry,
            ) = self._run_scoring_pipeline(
                narrator,
                reversal_context,
                max_rounds=self._max_reversal_rounds,
            )

            if replan_decision["status"] == "accepted":
                final_narration = replan_narration
                final_reports = replan_reports
                final_validator_reports = replan_validator_reports
                validation_revisions += replan_validation_revisions
                final_decision = replan_decision
                telemetry = replan_telemetry
                reversal["replan_passed"] = True

        return {
            "narration": final_narration,
            "judge_decision": final_decision,
            "critique_reports": final_reports,
            "telemetry": telemetry,
            "reversal": reversal,
            "validator_reports": final_validator_reports,
            "validation_revisions": validation_revisions,
        }


def build_default_coherence_gate(
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    max_tokens_per_role: dict[str, int] | None = None,
    wall_clock_timeout_ms: int = DEFAULT_WALL_CLOCK_TIMEOUT_MS,
    max_reversal_rounds: int = DEFAULT_MAX_REVERSAL_ROUNDS,
    time_source=None,
    max_validation_revisions: int = DEFAULT_MAX_VALIDATION_REVISIONS,
) -> CoherenceGate:
    critics: tuple[CritiqueAgent, ...] = (
        _DefaultCritic("continuity", "continuity"),
        _DefaultCritic("causality", "causality"),
        _DefaultCritic("dialogue_fit", "dialogue_fit"),
    )
    validators: tuple[CandidateValidator, ...] = (
        _EntityReachabilityValidator(),
        _InventoryLocationConsistencyValidator(),
        _CommittedStateContradictionValidator(),
        _BeatTransitionLegalityValidator(),
    )
    return CoherenceGate(
        critics=critics,
        validators=validators,
        threshold=DEFAULT_THRESHOLD,
        critical_floors=DEFAULT_CRITICAL_FLOORS,
        max_rounds=max_rounds,
        max_tokens_per_role=max_tokens_per_role,
        wall_clock_timeout_ms=wall_clock_timeout_ms,
        max_reversal_rounds=max_reversal_rounds,
        time_source=time_source,
        max_validation_revisions=max_validation_revisions,
    )
