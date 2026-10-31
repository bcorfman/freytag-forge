"""Turn-scoped batching and caching for independent Jev questions."""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from os import getenv
from threading import Thread
from typing import Any

from storygame.runtime.jev import noul_yes

Ask = Callable[[object, object], dict | None]


@dataclass(frozen=True)
class JevQuestion:
    """One individual question and its state, before it is put in a batch."""

    key: str
    state: object
    questions: dict[str, object]


@dataclass(frozen=True)
class _CachedAnswer:
    state_key: object
    question_key: object
    answer_key: str
    answer: object


class ConcurrentCall[T]:
    """Run one independent call on a daemon thread and re-raise its error on join."""

    def __init__(self, target: Callable[[], T]) -> None:
        self._target = target
        self._thread: Thread | None = None
        self._value: T | None = None
        self._error: BaseException | None = None

    def start(self) -> None:
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def join(self) -> T:
        if self._thread is None:
            raise RuntimeError("concurrent call was not started")
        self._thread.join()
        if self._error is not None:
            raise self._error
        return self._value  # type: ignore[return-value]

    def _run(self) -> None:
        try:
            self._value = self._target()
        except BaseException as error:
            self._error = error


def batching_enabled() -> bool:
    return getenv("FREYTAG_JEV_BATCH", "1") != "0"


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return ("dict", tuple(sorted((_freeze(key), _freeze(item)) for key, item in value.items())))
    if isinstance(value, list):
        return ("list", tuple(_freeze(item) for item in value))
    if isinstance(value, tuple):
        return ("tuple", tuple(_freeze(item) for item in value))
    if isinstance(value, set):
        return ("set", tuple(sorted(_freeze(item) for item in value)))
    try:
        hash(value)
    except TypeError:
        return (type(value).__name__, repr(value))
    return (type(value).__name__, value)


def _question_key(state: object, questions: object) -> tuple[object, object]:
    return _freeze(state), _freeze(questions)


def _answer_is_valid(answer: object) -> bool:
    return noul_yes(answer) is not None


class JevPrefetch:
    """Fetch independent questions once and serve only exact per-question hits."""

    def __init__(self, ask: Ask, questions: Iterable[JevQuestion], *, enabled: bool | None = None) -> None:
        self._ask = ask
        self._questions = tuple(questions)
        counts: dict[str, int] = {}
        for question in self._questions:
            counts[question.key] = counts.get(question.key, 0) + 1
        self._request_keys = tuple(
            question.key if counts[question.key] == 1 else f"{question.key}:{index}"
            for index, question in enumerate(self._questions)
        )
        self._enabled = batching_enabled() if enabled is None else enabled
        self._cached: dict[tuple[object, object], _CachedAnswer] = {}
        self._thread: Thread | None = None
        self._error: BaseException | None = None
        self._batch_unavailable = False

    @property
    def enabled(self) -> bool:
        return self._enabled and len(self._questions) > 1

    def start(self) -> None:
        if not self.enabled:
            return
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def join(self, *, raise_error: bool = True) -> None:
        if self._thread is not None:
            self._thread.join()
        if raise_error and self._error is not None:
            raise self._error

    def ask(self, state: object, questions: object) -> dict | None:
        if not self.enabled:
            return self._ask(state, questions)
        try:
            self.join()
        except BaseException:
            return self._ask(state, questions)
        if not isinstance(questions, dict) or len(questions) != 1:
            return self._ask(state, questions)
        answer_key = next(iter(questions))
        question_key = _question_key(state, questions)
        cached = self._cached.get(question_key)
        if cached is None or cached.answer_key != answer_key:
            if self._batch_unavailable and any(
                _question_key(question.state, question.questions) == question_key for question in self._questions
            ):
                return None
            return self._ask(state, questions)
        return {answer_key: copy.deepcopy(cached.answer)}

    def _run(self) -> None:
        try:
            answers = self._ask(self._batch_state(), self._batch_questions())
            if not isinstance(answers, dict):
                if answers is None:
                    self._batch_unavailable = True
                return
            for index, question in enumerate(self._questions):
                request_key = self._request_keys[index]
                answer = answers.get(request_key)
                if not _answer_is_valid(answer):
                    continue
                self._cached[_question_key(question.state, question.questions)] = _CachedAnswer(
                    _freeze(question.state),
                    _freeze(question.questions),
                    next(iter(question.questions)),
                    copy.deepcopy(answer),
                )
        except BaseException as error:
            self._error = error

    def _batch_questions(self) -> dict[str, object]:
        return {
            request_key: copy.deepcopy(next(iter(question.questions.values())))
            for request_key, question in zip(self._request_keys, self._questions, strict=True)
        }

    def _batch_state(self) -> dict[str, Any]:
        common: dict[str, object] = {}
        first = self._questions[0].state
        if isinstance(first, dict):
            for key, value in first.items():
                if all(
                    isinstance(question.state, dict) and question.state.get(key) == value
                    for question in self._questions
                ):
                    common[key] = copy.deepcopy(value)
        common["question_states"] = {
            request_key: copy.deepcopy(question.state)
            for request_key, question in zip(self._request_keys, self._questions, strict=True)
        }
        return common


def question_specs(
    command: str,
    *,
    relocates: Iterable[str] = (),
    boards: Iterable[str] = (),
    searches: Iterable[str] = (),
) -> tuple[JevQuestion, ...]:
    from storygame.runtime.jev_questions import (
        boards_vehicle_payload,
        relocates_thing_payload,
        searches_underneath_payload,
    )

    specs: list[JevQuestion] = []
    for name in relocates:
        state, questions = relocates_thing_payload(command, name)
        specs.append(JevQuestion("relocates_thing", state, questions))
    for name in boards:
        state, questions = boards_vehicle_payload(command, name)
        specs.append(JevQuestion("boards_vehicle", state, questions))
    for name in searches:
        state, questions = searches_underneath_payload(command, name)
        specs.append(JevQuestion("searches_underneath", state, questions))
    return tuple(specs)
