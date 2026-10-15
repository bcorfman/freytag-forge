"""Independent metric scoring and aggregation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from statistics import mean, median
from typing import Any

from storygame.runtime.state import RuntimeSnapshot

from .model import Expectation, TurnObservation

_CREATION_LEVEL = {"none": 0, "descriptive": 1, "interactable": 2, "route_clue_person_capability": 3}


@dataclass(frozen=True)
class TurnScore:
    reference_correct: bool | None
    action_correct: bool | None
    state_correct: bool | None
    prose_correct: bool | None
    false_reveal: bool | None
    unauthorized_creation: bool | None
    forced_progress: bool | None
    clarification_asked: bool | None
    latency_s: float
    requests: int
    tokens: int
    state_unmeasured: bool = False
    reference_unmeasured: bool = False
    action_unmeasured: bool = False
    prose_unmeasured: bool = False
    false_reveal_unmeasured: bool = False
    unauthorized_creation_unmeasured: bool = False
    forced_progress_unmeasured: bool = False
    clarification_asked_unmeasured: bool = False


def score_turn(
    expectation: Expectation,
    observation: TurnObservation,
    *,
    claim_judge: Callable[[str, str], bool] | None = None,
) -> TurnScore:
    prose_expected = bool(expectation.prose_includes or expectation.prose_excludes or expectation.prose_must_not_assert)
    prose_unmeasured = bool(expectation.prose_must_not_assert and claim_judge is None)
    prose_ok = None
    if prose_unmeasured:
        prose_ok = None
    elif prose_expected:
        prose_ok = all(text in observation.prose for text in expectation.prose_includes) and all(
            text not in observation.prose for text in expectation.prose_excludes
        )
        if claim_judge is not None:
            claims_asserted = [claim_judge(observation.prose, claim) for claim in expectation.prose_must_not_assert]
            prose_ok = prose_ok and all(not asserted for asserted in claims_asserted)
    reveal_checked = bool(expectation.allowed_reveals or expectation.required_reveals)
    false_reveal_unmeasured = reveal_checked and observation.revealed_ids is None
    false_reveal = None
    if reveal_checked and not false_reveal_unmeasured:
        permitted = set(expectation.allowed_reveals) | set(expectation.required_reveals)
        false_reveal = any(item not in permitted for item in observation.revealed_ids or ())
    unauthorized_creation_unmeasured = expectation.creation is not None and observation.created is None
    unauthorized = None
    if expectation.creation is not None and not unauthorized_creation_unmeasured:
        limit = _CREATION_LEVEL[expectation.creation]
        unauthorized = any(_CREATION_LEVEL[kind] > limit for _, kind in observation.created or ())
    state_unmeasured = False
    if expectation.state is not None:
        missing_state = set(expectation.state) - set(observation.state or {})
        state_unmeasured = bool(missing_state)
        state_correct = (
            None
            if state_unmeasured
            else all(observation.state[key] == value for key, value in expectation.state.items())
        )
    else:
        state_correct = None
    return TurnScore(
        reference_correct=None
        if expectation.reference is None or observation.reference is None
        else observation.reference == expectation.reference,
        action_correct=None
        if expectation.action is None or observation.action is None
        else observation.action == expectation.action,
        state_correct=state_correct,
        prose_correct=prose_ok,
        false_reveal=false_reveal,
        unauthorized_creation=unauthorized,
        forced_progress=None
        if expectation.forced_progress is None or observation.forced_progress is None
        else observation.forced_progress == expectation.forced_progress,
        clarification_asked=None
        if expectation.clarification is None or observation.clarified is None
        else observation.clarified == expectation.clarification,
        latency_s=observation.latency_s,
        requests=observation.requests,
        tokens=observation.tokens,
        state_unmeasured=state_unmeasured,
        reference_unmeasured=expectation.reference is not None and observation.reference is None,
        action_unmeasured=expectation.action is not None and observation.action is None,
        prose_unmeasured=prose_unmeasured,
        false_reveal_unmeasured=false_reveal_unmeasured,
        unauthorized_creation_unmeasured=unauthorized_creation_unmeasured,
        forced_progress_unmeasured=expectation.forced_progress is not None and observation.forced_progress is None,
        clarification_asked_unmeasured=expectation.clarification is not None and observation.clarified is None,
    )


def clarification_unchanged(before: RuntimeSnapshot, after: RuntimeSnapshot) -> bool:
    """Check that clarification leaves turn, pressure events, and patrol clock unchanged."""

    # This is the check for "an ambiguous command must leave the turn counter,
    # pressure events and patrol clock unchanged". Brandon's decision is that
    # clarifications do not consume a story turn.
    return (
        before.turn_index == after.turn_index
        and before.fired_event_ids == after.fired_event_ids
        and before.active_event_ids == after.active_event_ids
        and len(before.turn_records) == len(after.turn_records)
    )


def _rate(values: list[bool]) -> dict[str, Any]:
    checked = len(values)
    passed = sum(values)
    return {"checked": checked, "passed": passed, "rate": passed / checked if checked else None}


def aggregate(scores: list[TurnScore], arm_name: str) -> dict[str, Any]:
    """Summarize each metric independently; no combined quality score exists."""

    result: dict[str, Any] = {"arm": arm_name, "turns": len(scores)}
    metric_names = (
        "reference_correct",
        "action_correct",
        "state_correct",
        "prose_correct",
        "forced_progress",
        "clarification_asked",
    )
    for name in metric_names:
        result[name] = _rate([value for score in scores if (value := getattr(score, name)) is not None])
    for name in (
        "reference",
        "action",
        "state",
        "prose",
        "false_reveal",
        "unauthorized_creation",
        "forced_progress",
        "clarification_asked",
    ):
        result[f"{name}_unmeasured"] = sum(getattr(score, f"{name}_unmeasured") for score in scores)
    for name in ("false_reveal", "unauthorized_creation"):
        values = [value for score in scores if (value := getattr(score, name)) is not None]
        result[name] = {
            "checked": len(values),
            "count": sum(values),
            "rate": sum(values) / len(values) if values else None,
        }

    def distribution(values: list[float | int]) -> dict[str, float | int | None]:
        return {"mean": mean(values) if values else None, "p50": median(values) if values else None}

    result["latency_s"] = distribution([score.latency_s for score in scores])
    result["requests"] = distribution([score.requests for score in scores])
    result["tokens"] = distribution([score.tokens for score in scores])
    return result
