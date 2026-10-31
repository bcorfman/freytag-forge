"""Shadow verification of required observations in displayed narration."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from numbers import Real

from storygame.runtime.jev_prefetch import ConcurrentCall
from storygame.runtime.observation import ObservationContext
from storygame.runtime.opening_check import (
    OpeningVerdict,
    opening_payload,
    opening_verdict,
)

QUESTION_VERSION = "observation-relation-v1"


@dataclass(frozen=True)
class Relation:
    thing: str
    place: str | None = None
    holder: str | None = None
    scene_level: bool = False


def relations_from_context(context: ObservationContext) -> tuple[Relation, ...]:
    """Return required relations in the context's deterministic order."""
    relations = []
    for name in context.required:
        matching = next((thing for thing in context.visible_things if thing.name == name), None)
        if matching is None or matching.holder is not None:
            relations.append(Relation(thing=name))
        else:
            relations.append(Relation(thing=name, place=matching.place, scene_level=matching.scene_level))
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
    scene_state: bool = False
    opening_verdicts: tuple[OpeningVerdict, ...] = ()
    opening_requests: int = 0

    @property
    def accepted(self) -> bool:
        return (
            self.outcome == "ok"
            and all(verdict.verdict == "accept" for verdict in self.verdicts)
            and all(verdict.verdict == "accept" for verdict in self.opening_verdicts)
        )


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
        scene_state: bool = False,
        opening_check: bool = False,
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
        self.scene_state = scene_state
        self.opening_check = opening_check
        self._requests_this_turn = 0
        self._opening_requests_this_turn = 0

    def begin_turn(self) -> None:
        self._requests_this_turn = 0
        self._opening_requests_this_turn = 0

    def verify(
        self,
        narration: str,
        relations: Sequence[Relation],
        *,
        scene: str | None = None,
        opening_subjects: Sequence[str] = (),
        command: str = "",
        story_text: str | None = None,
    ) -> VerifierReport:
        relations = tuple(relations)
        opening_subjects = tuple(opening_subjects)
        if self.opening_check and opening_subjects:
            return self._verify_with_openings(
                narration,
                relations,
                opening_subjects,
                command,
                scene,
                story_text=story_text,
            )
        if not relations:
            return VerifierReport((), "no_relations", 0, 0.0, None)
        if self._requests_this_turn >= self._max_requests_per_turn:
            verdicts = tuple(RelationVerdict(relation, "unavailable", None) for relation in relations)
            return VerifierReport(verdicts, "budget_exhausted", 0, 0.0, "request_budget")

        questions = {f"relation_{index}": _question_for(relation) for index, relation in enumerate(relations)}
        state = self._state_for(narration, relations, scene)
        scene_state_sent = "starting_places" in state
        self._requests_this_turn += 1
        started = self._clock()
        try:
            answers = self._ask(state, questions)
        except Exception:
            elapsed_s = self._clock() - started
            verdicts = tuple(RelationVerdict(relation, "unavailable", None) for relation in relations)
            return VerifierReport(verdicts, "unavailable", 1, elapsed_s, "ask_raised", scene_state_sent)
        elapsed_s = self._clock() - started

        if answers is None:
            verdicts = tuple(RelationVerdict(relation, "unavailable", None) for relation in relations)
            return VerifierReport(verdicts, "unavailable", 1, elapsed_s, "ask_returned_none", scene_state_sent)

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
        return VerifierReport(tuple(verdicts), outcome, 1, elapsed_s, failure, scene_state_sent)

    def _verify_with_openings(
        self,
        narration: str,
        relations: Sequence[Relation],
        opening_subjects: Sequence[str],
        command: str,
        scene: str | None,
        *,
        story_text: str | None = None,
    ) -> VerifierReport:
        relation_questions = {f"relation_{index}": _question_for(relation) for index, relation in enumerate(relations)}
        relation_state = self._state_for(narration, relations, scene)
        scene_state_sent = "starting_places" in relation_state
        relation_call = None
        relation_requests = 0
        relation_budget_exhausted = False
        if relations:
            if self._requests_this_turn >= self._max_requests_per_turn:
                relation_budget_exhausted = True
            else:
                self._requests_this_turn += 1
                relation_requests = 1
                relation_call = ConcurrentCall(
                    lambda state=relation_state, questions=relation_questions: self._ask(state, questions)
                )

        opening_calls = []
        opening_verdicts: list[OpeningVerdict | None] = [None] * len(opening_subjects)
        for index, thing in enumerate(opening_subjects):
            if self._opening_requests_this_turn >= 2:
                opening_verdicts[index] = OpeningVerdict(thing, "unavailable", None)
                continue
            state, questions = opening_payload(narration, thing, command, story_text=story_text)
            opening_call = ConcurrentCall(lambda state=state, questions=questions: self._ask(state, questions))
            opening_calls.append((index, thing, opening_call))
            self._opening_requests_this_turn += 1

        started = self._clock()
        if relation_call is not None:
            relation_call.start()
        for _index, _thing, opening_call in opening_calls:
            opening_call.start()

        relation_answers = None
        relation_failure = None
        if relation_call is not None:
            try:
                relation_answers = relation_call.join()
            except Exception:
                relation_failure = "ask_raised"
        for index, thing, opening_call in opening_calls:
            try:
                answers = opening_call.join()
            except Exception:
                answers = None
            opening_verdicts[index] = opening_verdict(
                thing,
                answers,
                accept_above=self._accept_above,
                reject_below=self._reject_below,
            )
        elapsed_s = self._clock() - started

        relation_verdicts, relation_outcome, failure = self._relation_result(
            relations,
            relation_answers,
            relation_failure,
            relation_budget_exhausted,
        )
        completed_opening_verdicts = tuple(verdict for verdict in opening_verdicts if verdict is not None)
        opening_outcome, opening_failure = _opening_outcome(completed_opening_verdicts, len(opening_calls))
        if relation_outcome not in {"ok", "no_relations"}:
            outcome = relation_outcome
            combined_failure = failure
        else:
            outcome = opening_outcome
            combined_failure = opening_failure
        return VerifierReport(
            tuple(relation_verdicts),
            outcome,
            relation_requests,
            elapsed_s,
            combined_failure,
            scene_state_sent,
            completed_opening_verdicts,
            len(opening_calls),
        )

    def _relation_result(
        self,
        relations: Sequence[Relation],
        answers: object,
        failure: str | None,
        budget_exhausted: bool,
    ) -> tuple[list[RelationVerdict], str, str | None]:
        if not relations:
            return [], "no_relations", None
        if budget_exhausted:
            return (
                [RelationVerdict(relation, "unavailable", None) for relation in relations],
                "budget_exhausted",
                "request_budget",
            )
        if failure is not None:
            return (
                [RelationVerdict(relation, "unavailable", None) for relation in relations],
                "unavailable",
                failure,
            )
        if answers is None:
            return (
                [RelationVerdict(relation, "unavailable", None) for relation in relations],
                "unavailable",
                "ask_returned_none",
            )
        verdicts = []
        valid_count = 0
        first_failure = None
        for index, relation in enumerate(relations):
            key = f"relation_{index}"
            score = _score_for(answers, key)
            if score is None:
                verdicts.append(RelationVerdict(relation, "unavailable", None))
                if first_failure is None:
                    first_failure = (
                        f"missing_answer:{index}" if not _has_answer(answers, key) else f"invalid_answer:{index}"
                    )
                continue
            valid_count += 1
            verdicts.append(
                RelationVerdict(relation, _verdict_for(score, self._accept_above, self._reject_below), score)
            )
        if valid_count == 0:
            return verdicts, "malformed", "no_valid_answers"
        if valid_count < len(relations):
            return verdicts, "partial", first_failure
        return verdicts, "ok", None

    def _state_for(self, narration: str, relations: Sequence[Relation], scene: str | None) -> dict[str, object]:
        if self.scene_state and scene is not None:
            starting_places = {relation.thing: relation.place for relation in relations if relation.scene_level}
            if starting_places:
                return {"narration": narration, "scene": scene, "starting_places": starting_places}
        return {"narration": narration}


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


def _opening_outcome(verdicts: tuple[OpeningVerdict, ...], requested: int) -> tuple[str, str | None]:
    if not verdicts and requested == 0:
        return "no_relations", None
    if any(verdict.verdict == "unavailable" for verdict in verdicts):
        return "unavailable", "opening_unavailable"
    return "ok", None
