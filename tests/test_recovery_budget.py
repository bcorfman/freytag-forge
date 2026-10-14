"""Hermetic coverage for the shared two-request narration budget."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
LEAK = "Rebecca's secured office can broadcast the evidence."
CLEAN = "Kristin considers whether to transmit the evidence."
COMMAND = "Assess the cost of transmitting our evidence."


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _proposal(text: str) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []}


def _scene_2c_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2C")
    state.current_scene_id = "2C"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("2C")
    return state


def _engine_with_transport(
    monkeypatch: pytest.MonkeyPatch, *script: object
) -> tuple[RuntimeEngine, RuntimeState, list[str]]:
    state = _scene_2c_state()
    prompts: list[str] = []
    remaining = list(script)

    def open_request(request: object, **_kwargs: object) -> _Response:
        payload = json.loads(request.data)  # type: ignore[attr-defined]
        prompts.append(payload["system"])
        response = remaining.pop(0)
        if isinstance(response, BaseException):
            raise response
        if response == "malformed":
            return _Response({"narration": "not valid json"})
        return _Response({"narration": json.dumps(_proposal(response))})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return RuntimeEngine(state, provider), state, prompts


def test_budget_good_reply_uses_one_http_request(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, state, _prompts = _engine_with_transport(monkeypatch, CLEAN)

    result = engine.turn(COMMAND)

    assert result.segments[0].text == CLEAN
    assert engine.provider.request_count == 1
    assert state.turn_index == 1


def test_budget_transient_retry_uses_two_http_requests_and_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, _state, _prompts = _engine_with_transport(monkeypatch, URLError("offline"), CLEAN)

    result = engine.turn(COMMAND)

    assert result.segments[0].text == CLEAN
    assert engine.provider.request_count == 2


def test_budget_malformed_recovery_uses_two_http_requests_and_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, _state, _prompts = _engine_with_transport(monkeypatch, "malformed", CLEAN)

    result = engine.turn(COMMAND)

    assert result.segments[0].text == CLEAN
    assert engine.provider.request_count == 2


def test_budget_guard_retry_uses_two_http_requests_and_sets_guard_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, state, _prompts = _engine_with_transport(monkeypatch, LEAK, CLEAN)

    result = engine.turn(COMMAND)

    assert result.segments[0].text == CLEAN
    assert engine.provider.request_count == 2
    assert state.last_turn_delivery.guard_retry_used is True


def test_budget_transient_then_guard_rejection_fails_closed_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, state, _prompts = _engine_with_transport(monkeypatch, URLError("offline"), LEAK)
    before = state.snapshot()

    with pytest.raises(ProposalValidationError) as caught:
        engine.turn(COMMAND)

    assert caught.value.code == "narration_known_term_leak"
    assert engine.provider.request_count == 2
    assert state.snapshot() == before


def test_budget_malformed_then_still_bad_raises_typed_error_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, state, _prompts = _engine_with_transport(monkeypatch, "malformed", "malformed")
    before = state.snapshot()

    with pytest.raises(NarrationProviderError):
        engine.turn(COMMAND)

    assert engine.provider.request_count == 2
    assert state.snapshot() == before


def test_budget_guard_rejection_twice_uses_two_http_requests_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, state, _prompts = _engine_with_transport(monkeypatch, LEAK, LEAK)
    before = state.snapshot()

    with pytest.raises(ProposalValidationError) as caught:
        engine.turn(COMMAND)

    assert caught.value.code == "narration_known_term_leak"
    assert engine.provider.request_count == 2
    assert state.snapshot() == before


def test_budget_guard_retry_feedback_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, _state, prompts = _engine_with_transport(monkeypatch, LEAK, CLEAN)

    engine.turn(COMMAND)

    assert len(prompts) == 2
    assert "Your last reply named something the player has not met yet." in prompts[1]
    assert "Rebecca's secured office" not in "\n".join(prompts)
    assert "narration mentions an unavailable entity" not in "\n".join(prompts)


def test_budget_reset_allows_provider_call_outside_successful_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, _state, _prompts = _engine_with_transport(monkeypatch, LEAK, CLEAN, CLEAN)

    engine.turn(COMMAND)
    reply = engine.provider(COMMAND)

    assert reply["segments"][0]["text"] == CLEAN
    assert engine.provider.request_count == 3


def test_budget_reset_allows_provider_call_outside_failed_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, _state, _prompts = _engine_with_transport(monkeypatch, LEAK, LEAK, CLEAN)

    with pytest.raises(ProposalValidationError):
        engine.turn(COMMAND)
    reply = engine.provider(COMMAND)

    assert reply["segments"][0]["text"] == CLEAN
    assert engine.provider.request_count == 3


def test_budget_reset_gives_next_engine_turn_two_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, _state, _prompts = _engine_with_transport(monkeypatch, LEAK, CLEAN, LEAK, CLEAN)

    engine.turn(COMMAND)
    engine.provider(COMMAND)
    result = engine.turn(COMMAND)

    assert result.segments[0].text == CLEAN
    assert engine.provider.request_count == 4
