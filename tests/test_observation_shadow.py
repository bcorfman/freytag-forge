from __future__ import annotations

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.observation import ObservationRequest, ObservationScopeTooLarge
from storygame.runtime.observation_verifier import ObservationVerifier
from tests.test_observation_mode import _state_at


def _provider():
    state = _state_at("outside_house", already_aboard=True)
    provider = build_capture_provider(state)
    provider.observation_request = ObservationRequest("Inspect the truck.", "enter", "kristin_truck")
    return state, provider


def _capture(provider, verifier=None, ask=None):
    capture = WorldCapture(provider, ask or (lambda _state, _questions: {}))
    capture.shadow_verifier = verifier
    return capture


def _shadow_ask(calls, score):
    def ask(state, questions):
        calls.append((state, questions))
        return {key: {"noul": score} for key in questions}

    return ask


def _commit(capture, narration="The observed details remain unchanged."):
    return capture.after_commit("Inspect the truck.", narration, entered_scene=False)


def test_shadow_is_off_by_default_and_does_not_ask() -> None:
    state, provider = _provider()
    calls = []
    capture = _capture(provider, ask=_shadow_ask(calls, 1.0))

    record = _commit(capture)

    assert "observation_shadow" not in record
    assert calls == []
    assert capture.last_after is record
    assert state.snapshot().facts == state.facts


def test_shadow_records_verdicts_and_sends_narration_once() -> None:
    _state, provider = _provider()
    calls = []
    verifier = ObservationVerifier(_shadow_ask(calls, 1.0))
    capture = _capture(provider, verifier)
    narration = "The observed details remain unchanged."

    record = _commit(capture, narration)

    shadow = record["observation_shadow"]
    assert shadow["outcome"] == "ok"
    assert shadow["requests"] == 1
    assert shadow["accepted"] is True
    assert shadow["failure"] is None
    assert shadow["question_version"] == ObservationVerifier.QUESTION_VERSION
    assert shadow["verdicts"]
    assert all(verdict["verdict"] == "accept" for verdict in shadow["verdicts"])
    assert len(calls) == 1
    assert calls[0][0]["narration"] == narration


def test_rejecting_shadow_changes_no_other_record_or_world_field() -> None:
    baseline_state, baseline_provider = _provider()
    baseline = _commit(_capture(baseline_provider))
    state, provider = _provider()
    calls = []
    capture = _capture(provider, ObservationVerifier(_shadow_ask(calls, 0.0)))
    before = state.snapshot()

    record = _commit(capture)

    without_shadow = {key: value for key, value in record.items() if key != "observation_shadow"}
    assert without_shadow == baseline
    assert state.snapshot() == before
    assert state.facts == baseline_state.facts
    assert record["observation_shadow"]["accepted"] is False
    assert all(verdict["verdict"] == "reject" for verdict in record["observation_shadow"]["verdicts"])


def test_none_answer_is_recorded_without_changing_the_turn() -> None:
    state, provider = _provider()
    capture = _capture(provider, ObservationVerifier(lambda _state, _questions: None))
    before = state.snapshot()

    shadow = _commit(capture)["observation_shadow"]

    assert shadow["outcome"] == "unavailable"
    assert shadow["requests"] == 1
    assert shadow["failure"] == "ask_returned_none"
    assert shadow["accepted"] is False
    assert state.snapshot() == before


def test_ask_exception_is_swallowed_without_narration_in_failure() -> None:
    narration = "A narration that must not enter a failure field."

    def ask(_state, _questions):
        raise RuntimeError(narration)

    _state, provider = _provider()
    record = _commit(_capture(provider, ObservationVerifier(ask)), narration)

    shadow = record["observation_shadow"]
    assert shadow["outcome"] == "unavailable"
    assert shadow["failure"] == "ask_raised"
    assert narration not in str(shadow["failure"])


def test_shadow_exception_is_swallowed_with_exception_class() -> None:
    _state, provider = _provider()
    verifier = ObservationVerifier(lambda _state, _questions: {})

    def explode(_narration, _relations):
        raise LookupError("shadow failure")

    verifier.verify = explode
    record = _commit(_capture(provider, verifier))

    assert record["observation_shadow"] == {
        "outcome": "shadow_error",
        "requests": 0,
        "elapsed_s": 0.0,
        "failure": "LookupError",
        "question_version": ObservationVerifier.QUESTION_VERSION,
        "accepted": False,
        "verdicts": [],
    }


def test_no_observation_request_does_not_add_shadow_or_ask() -> None:
    _state, provider = _provider()
    provider.observation_request = None
    calls = []
    capture = _capture(provider, ObservationVerifier(_shadow_ask(calls, 1.0)))

    record = _commit(capture)

    assert "observation_shadow" not in record
    assert calls == []


def test_observation_scope_error_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    _state, provider = _provider()
    calls = []
    capture = _capture(provider, ObservationVerifier(_shadow_ask(calls, 1.0)))

    def raise_scope_error():
        raise ObservationScopeTooLarge("required observation scope is too large")

    monkeypatch.setattr(provider, "_observation_context", raise_scope_error)

    record = _commit(capture)

    assert record["observation_shadow"]["failure"] == "ObservationScopeTooLarge"
    assert record["observation_shadow"]["outcome"] == "shadow_error"
    assert record["observation_shadow"]["verdicts"] == []
    assert calls == []
