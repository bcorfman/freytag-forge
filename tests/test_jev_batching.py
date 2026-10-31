from __future__ import annotations

from copy import deepcopy
from time import monotonic, sleep

import pytest

from storygame.runtime.jev_prefetch import ConcurrentCall, JevPrefetch, question_specs
from storygame.runtime.jev_questions import (
    boards_vehicle,
    only_boards_vehicle,
    relocates_thing,
    searches_underneath,
)


def _fake_jev(calls: list[tuple[object, object]], *, malformed: set[str] | None = None):
    malformed = malformed or set()

    def ask(state, questions):
        calls.append((deepcopy(state), deepcopy(questions)))
        answers = {}
        states = state.get("question_states", {}) if isinstance(state, dict) else {}
        for key in questions:
            answer_key = key.split(":", 1)[0]
            if len(questions) > 1 and answer_key in malformed:
                answers[key] = {"noul": "bad"}
                continue
            question_state = states.get(key, state) if isinstance(states, dict) else state
            value = {
                "relocates_thing": 0.2,
                "boards_vehicle": 0.8,
                "searches_underneath": 0.2 if question_state.get("thing") == "missing" else 0.8,
                "only_boards_vehicle": 0.8,
            }.get(answer_key, 0.8)
            answers[key] = {"noul": value, "state_seen": deepcopy(question_state)}
        return answers

    return ask


def _questions(calls, index: int = 0):
    return calls[index][1]


def test_prefetch_batches_independent_questions_and_later_stages_hit_cache() -> None:
    calls: list[tuple[object, object]] = []
    ask = _fake_jev(calls)
    prefetch = JevPrefetch(
        ask,
        question_specs(
            "Look under the bench.",
            relocates=("fixed bench",),
            boards=("truck",),
            searches=("bench",),
        ),
    )
    prefetch.start()

    assert relocates_thing(prefetch.ask, "Look under the bench.", "fixed bench") is False
    assert boards_vehicle(prefetch.ask, "Look under the bench.", "truck") is True
    assert searches_underneath(prefetch.ask, "Look under the bench.", "bench") is True
    assert len(calls) == 1
    assert set(_questions(calls)) == {"relocates_thing", "boards_vehicle", "searches_underneath"}


def test_unprefetched_question_falls_back_to_one_individual_call() -> None:
    calls: list[tuple[object, object]] = []
    prefetch = JevPrefetch(
        _fake_jev(calls),
        question_specs("Look under the bench.", boards=("truck",), searches=("bench",)),
    )
    prefetch.start()

    assert boards_vehicle(prefetch.ask, "Look under the bench.", "truck") is True
    assert relocates_thing(prefetch.ask, "Look under the bench.", "loose card") is False
    assert len(calls) == 2
    assert set(_questions(calls, 1)) == {"relocates_thing"}


def test_only_boards_vehicle_is_never_prefetched_and_is_asked_after_yes() -> None:
    calls: list[tuple[object, object]] = []
    prefetch = JevPrefetch(
        _fake_jev(calls),
        question_specs("Get into the truck.", boards=("truck",), searches=("bench",)),
    )
    prefetch.start()

    assert boards_vehicle(prefetch.ask, "Get into the truck.", "truck") is True
    assert only_boards_vehicle(prefetch.ask, "Get into the truck.", "truck") is True
    assert "only_boards_vehicle" not in calls[0][1]
    assert [next(iter(questions)) for _, questions in calls] == [
        "boards_vehicle",
        "only_boards_vehicle",
    ]


@pytest.mark.parametrize("malformed", [set(), {"searches_underneath"}])
def test_missing_or_malformed_cached_answer_falls_back(malformed: set[str]) -> None:
    calls: list[tuple[object, object]] = []
    ask = _fake_jev(calls, malformed=malformed)
    prefetch = JevPrefetch(
        ask,
        question_specs("Look under the bench.", boards=("truck",), searches=("bench",)),
    )
    prefetch.start()

    if malformed:
        assert searches_underneath(prefetch.ask, "Look under the bench.", "bench") is True
        assert len(calls) == 2
    else:
        assert searches_underneath(prefetch.ask, "Look under the bench.", "missing") is False
        assert len(calls) == 2


def test_cache_does_not_cross_turns() -> None:
    calls: list[tuple[object, object]] = []
    ask = _fake_jev(calls)
    first = JevPrefetch(ask, question_specs("Inspect the bench.", boards=("truck",), searches=("bench",)))
    first.start()
    assert boards_vehicle(first.ask, "Inspect the bench.", "truck") is True

    second = JevPrefetch(ask, question_specs("Inspect the bench.", boards=("truck",), searches=("bench",)))
    second.start()
    assert boards_vehicle(second.ask, "Inspect the bench.", "truck") is True
    assert len(calls) == 2


def test_batching_flag_off_restores_individual_call_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FREYTAG_JEV_BATCH", "0")
    calls: list[tuple[object, object]] = []
    prefetch = JevPrefetch(
        _fake_jev(calls),
        question_specs("Look under the bench.", boards=("truck",), searches=("bench",)),
    )
    prefetch.start()

    assert boards_vehicle(prefetch.ask, "Look under the bench.", "truck") is True
    assert searches_underneath(prefetch.ask, "Look under the bench.", "bench") is True
    assert len(calls) == 2
    assert all(len(questions) == 1 for _, questions in calls)


def test_prefetch_and_referent_calls_overlap() -> None:
    started: list[str] = []

    def operation(name: str) -> str:
        started.append(name)
        sleep(0.08)
        return name

    first = ConcurrentCall(lambda: operation("prefetch"))
    second = ConcurrentCall(lambda: operation("referent"))
    began = monotonic()
    first.start()
    second.start()
    assert {first.join(), second.join()} == {"prefetch", "referent"}
    assert monotonic() - began < 0.14
    assert set(started) == {"prefetch", "referent"}


@pytest.mark.parametrize("name", ["prefetch", "referent"])
def test_concurrent_call_surfaces_its_exception(name: str) -> None:
    error = RuntimeError(name)
    call = ConcurrentCall(lambda: (_ for _ in ()).throw(error))
    call.start()
    with pytest.raises(RuntimeError) as caught:
        call.join()
    assert str(caught.value) == name


def test_answers_match_with_batching_on_and_off(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(enabled: bool) -> tuple[bool | None, bool | None]:
        calls: list[tuple[object, object]] = []
        prefetch = JevPrefetch(
            _fake_jev(calls),
            question_specs("Look under the bench.", boards=("truck",), searches=("bench",)),
            enabled=enabled,
        )
        prefetch.start()
        return (
            boards_vehicle(prefetch.ask, "Look under the bench.", "truck"),
            searches_underneath(prefetch.ask, "Look under the bench.", "bench"),
        )

    monkeypatch.delenv("FREYTAG_JEV_BATCH", raising=False)
    assert run(True) == run(False)
