"""Shadow verification of required observations in displayed narration."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from numbers import Real

from storygame.runtime.observation import ObservationContext

QUESTION_VERSION = "observation-relation-v1"


@dataclass(frozen=True)
class Relation:
    thing: str
    place: str | None = None
    holder: str | None = None


def relations_from_context(context: ObservationContext) -> tuple[Relation, ...]:
    """Return required relations in the context's deterministic order."""
    relations = []
    for name in context.required:
        matching = next((thing for thing in context.visible_things if thing.name == name), None)
        if matching is None or matching.holder is not None:
            relations.append(Relation(thing=name))
        else:
            relations.append(Relation(thing=name, place=matching.place))
    return tuple(relations)


@dataclass(frozen=True)
class RelationVerdict:
    relation: Relation
    verdict: str
    score: float | None


@dataclass(frozen=True)
class VerifierReport:
    verdicts: tuple[RelationVerdict, ...]
    outcome: str
    requests: int
    elapsed_s: float
    failure: str | None

    @property
    def accepted(self) -> bool:
        return self.outcome == "ok" and all(verdict.verdict == "accept" for verdict in self.verdicts)


class ObservationVerifier:
    """Injectable, fail-closed verifier intended for shadow-only use."""

    QUESTION_VERSION = QUESTION_VERSION

    def __init__(
        self,
        ask: Callable[[object, object], dict | None],
        *,
        accept_above: float = 0.65,
        reject_below: float = 0.35,
        max_requests_per_turn: int = 2,
        clock=time.monotonic,
    ) -> None:
        if not 0 <= reject_below < accept_above <= 1:
            raise ValueError("thresholds must satisfy 0 <= reject_below < accept_above <= 1")
        if max_requests_per_turn < 0:
            raise ValueError("max_requests_per_turn must be non-negative")
        self._ask = ask
        self._accept_above = accept_above
        self._reject_below = reject_below
        self._max_requests_per_turn = max_requests_per_turn
        self._clock = clock
        self._requests_this_turn = 0

    def begin_turn(self) -> None:
        self._requests_this_turn = 0

    def verify(self, narration: str, relations: Sequence[Relation]) -> VerifierReport:
        relations = tuple(relations)
        if not relations:
            return VerifierReport((), "no_relations", 0, 0.0, None)
        if self._requests_this_turn >= self._max_requests_per_turn:
            verdicts = tuple(RelationVerdict(relation, "unavailable", None) for relation in relations)
            return VerifierReport(verdicts, "budget_exhausted", 0, 0.0, "request_budget")

        questions = {f"relation_{index}": _question_for(relation) for index, relation in enumerate(relations)}
        state = {"narration": narration}
        self._requests_this_turn += 1
        started = self._clock()
        try:
            answers = self._ask(state, questions)
        except Exception:
            elapsed_s = self._clock() - started
            verdicts = tuple(RelationVerdict(relation, "unavailable", None) for relation in relations)
            return VerifierReport(verdicts, "unavailable", 1, elapsed_s, "ask_raised")
        elapsed_s = self._clock() - started

        if answers is None:
            verdicts = tuple(RelationVerdict(relation, "unavailable", None) for relation in relations)
            return VerifierReport(verdicts, "unavailable", 1, elapsed_s, "ask_returned_none")

        verdicts = []
        valid_count = 0
        first_failure = None
        for index, relation in enumerate(relations):
            key = f"relation_{index}"
            score = _score_for(answers, key)
            if score is None:
                verdicts.append(RelationVerdict(relation, "unavailable", None))
                if first_failure is None:
                    if not _has_answer(answers, key):
                        first_failure = f"missing_answer:{index}"
                    else:
                        first_failure = f"invalid_answer:{index}"
                continue
            valid_count += 1
            verdict = _verdict_for(score, self._accept_above, self._reject_below)
            verdicts.append(RelationVerdict(relation, verdict, score))

        if valid_count == 0:
            outcome = "malformed"
            failure = "no_valid_answers"
        elif valid_count < len(relations):
            outcome = "partial"
            failure = first_failure
        else:
            outcome = "ok"
            failure = None
        return VerifierReport(tuple(verdicts), outcome, 1, elapsed_s, failure)


def _question_for(relation: Relation) -> dict[str, object]:
    location = _location_text(relation)
    target = f"{relation.thing}{location}"
    instructions = (
        "You are a continuity editor for an interactive story. "
        f"Check whether the narration shows the thing named {target} as a present fact at its permitted relation. "
        "The narration does NOT show it when it is missing, only imagined, remembered, denied, elsewhere, "
        "with someone else, or not mentioned."
    )
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {
            "true": f"The narration shows {target} as a present fact at its permitted relation.",
            "false": (
                f"The narration does not show {target} as a present fact at its permitted relation, "
                "including when it is missing, imagined, remembered, denied, elsewhere, with someone else, "
                "or not mentioned."
            ),
        },
    }


def _location_text(relation: Relation) -> str:
    facts = []
    if relation.place is not None and relation.place == relation.holder:
        facts.append(f"held by {relation.holder}")
    elif relation.place is not None:
        facts.append(f"at place {relation.place}")
    if relation.holder is not None and relation.place != relation.holder:
        facts.append(f"held by {relation.holder}")
    return f" ({' and '.join(facts)})" if facts else ""


def _has_answer(answers: object, key: str) -> bool:
    return isinstance(answers, dict) and key in answers


def _score_for(answers: object, key: str) -> float | None:
    if not isinstance(answers, dict) or key not in answers:
        return None
    answer = answers[key]
    if not isinstance(answer, dict):
        return None
    score = answer.get("noul")
    if isinstance(score, bool) or not isinstance(score, Real) or not 0 <= score <= 1:
        return None
    return float(score)


def _verdict_for(score: float, accept_above: float, reject_below: float) -> str:
    if score > accept_above:
        return "accept"
    if score < reject_below:
        return "reject"
    return "uncertain"
