import pytest

from storygame.runtime.observation import ObservationContext, ObservedThing
from storygame.runtime.observation_verifier import (
    ObservationVerifier,
    Relation,
    relations_from_context,
)


def _context() -> ObservationContext:
    return ObservationContext(
        observer="observer",
        action="inspect",
        completed_actions=(),
        visible_things=(
            ObservedThing(name="amber token", place="stone shelf"),
            ObservedThing(name="blue seal", place=None, holder="keeper"),
        ),
        contingent_things=(),
        required=("blue seal", "missing charm", "amber token"),
        omitted_optional=(),
        scope_complete=True,
    )


def _relation() -> Relation:
    return Relation(thing="amber token", place="stone shelf")


def _answers(questions: dict, score: object = 0.9) -> dict:
    return {key: {"noul": score} for key in questions}


def test_relations_from_context_preserves_required_order_and_placement() -> None:
    assert relations_from_context(_context()) == (
        Relation(thing="blue seal"),
        Relation(thing="missing charm"),
        Relation(thing="amber token", place="stone shelf"),
    )


def test_verify_batches_one_question_per_relation_and_includes_narration() -> None:
    calls: list[tuple[object, object]] = []

    def ask(state: object, questions: object) -> dict:
        calls.append((state, questions))
        return _answers(questions)

    relations = (_relation(), Relation(thing="blue seal", holder="keeper"))
    report = ObservationVerifier(ask).verify("The amber token rests on the stone shelf.", relations)

    assert report.outcome == "ok"
    assert report.requests == 1
    assert len(calls) == 1
    state, questions = calls[0]
    assert state == {"narration": "The amber token rests on the stone shelf."}
    assert list(questions) == ["relation_0", "relation_1"]
    assert all(question["type"] == "noul" for question in questions.values())
    assert "amber token" in questions["relation_0"]["instructions"]
    assert "stone shelf" in questions["relation_0"]["instructions"]
    assert "narration" in questions["relation_0"]["instructions"]
    assert "blue seal" in questions["relation_1"]["instructions"]
    assert "keeper" in questions["relation_1"]["instructions"]


@pytest.mark.parametrize(
    ("score", "expected"),
    ((0.66, "accept"), (0.65, "uncertain"), (0.35, "uncertain"), (0.34, "reject")),
)
def test_thresholds_are_strict(score: float, expected: str) -> None:
    verifier = ObservationVerifier(lambda _state, questions: _answers(questions, score))

    report = verifier.verify("The amber token is present.", (_relation(),))

    assert report.verdicts[0].verdict == expected
    assert report.accepted is (expected == "accept")


def test_ask_none_is_unavailable() -> None:
    report = ObservationVerifier(lambda _state, _questions: None).verify("opaque narration", (_relation(),))

    assert report.outcome == "unavailable"
    assert report.failure == "ask_returned_none"
    assert report.requests == 1
    assert report.verdicts[0].verdict == "unavailable"
    assert report.verdicts[0].score is None


def test_ask_exception_is_unavailable_without_escaping_or_leaking_text() -> None:
    narration = "private narration that must not become a failure code"

    def ask(_state: object, _questions: object) -> None:
        raise RuntimeError(narration)

    report = ObservationVerifier(ask).verify(narration, (_relation(),))

    assert report.outcome == "unavailable"
    assert report.failure == "ask_raised"
    assert narration not in (report.failure or "")
    assert report.verdicts[0].verdict == "unavailable"


def test_missing_answer_is_partial_and_unavailable() -> None:
    def ask(_state: object, _questions: dict) -> dict:
        return {"relation_0": {"noul": 0.9}}

    relations = (_relation(), Relation(thing="blue seal", holder="keeper"))
    report = ObservationVerifier(ask).verify("The things are present.", relations)

    assert report.outcome == "partial"
    assert report.verdicts[0].verdict == "accept"
    assert report.verdicts[1].verdict == "unavailable"
    assert report.verdicts[1].score is None
    assert report.accepted is False


@pytest.mark.parametrize("answer", (True, "0.9"))
def test_bool_or_string_score_is_unavailable(answer: object) -> None:
    report = ObservationVerifier(lambda _state, _questions: {"relation_0": {"noul": answer}}).verify(
        "The amber token is present.", (_relation(),)
    )

    assert report.outcome == "malformed"
    assert report.verdicts[0].verdict == "unavailable"


def test_all_answers_malformed_is_malformed() -> None:
    def ask(_state: object, questions: dict) -> dict:
        return {key: {"noul": 2} for key in questions}

    report = ObservationVerifier(ask).verify("The amber token is present.", (_relation(),))

    assert report.outcome == "malformed"
    assert report.failure == "no_valid_answers"


def test_per_turn_budget_and_begin_turn_reset() -> None:
    calls = 0

    def ask(_state: object, questions: dict) -> dict:
        nonlocal calls
        calls += 1
        return _answers(questions)

    verifier = ObservationVerifier(ask, max_requests_per_turn=2)
    assert verifier.verify("one", (_relation(),)).outcome == "ok"
    assert verifier.verify("two", (_relation(),)).outcome == "ok"
    exhausted = verifier.verify("three", (_relation(),))
    assert exhausted.outcome == "budget_exhausted"
    assert exhausted.requests == 0
    assert exhausted.failure == "request_budget"
    assert calls == 2

    verifier.begin_turn()
    assert verifier.verify("four", (_relation(),)).outcome == "ok"
    assert calls == 3


def test_no_relations_does_not_call_ask() -> None:
    calls = 0

    def ask(_state: object, _questions: object) -> None:
        nonlocal calls
        calls += 1

    report = ObservationVerifier(ask).verify("nothing to check", ())

    assert report.outcome == "no_relations"
    assert report.requests == 0
    assert report.verdicts == ()
    assert calls == 0


@pytest.mark.parametrize(
    ("accept_above", "reject_below"),
    ((0.0, 0.0), (0.5, 0.5), (1.1, 0.5), (0.5, -0.1)),
)
def test_invalid_thresholds_raise_value_error(accept_above: float, reject_below: float) -> None:
    with pytest.raises(ValueError):
        ObservationVerifier(lambda _state, _questions: None, accept_above=accept_above, reject_below=reject_below)


def test_elapsed_time_uses_injected_clock_around_request() -> None:
    ticks = iter((10.0, 10.25))
    verifier = ObservationVerifier(
        lambda _state, questions: _answers(questions),
        clock=lambda: next(ticks),
    )

    report = verifier.verify("The amber token is present.", (_relation(),))

    assert report.elapsed_s == 0.25
