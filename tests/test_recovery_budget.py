"""Hermetic coverage for the shared two-request narration budget."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import _MATCH_SYSTEM, ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
LEAK = "Rebecca's secured office can broadcast the evidence."
CLEAN = "Kristin considers whether to transmit the evidence."
COMMAND = "Assess the cost of transmitting our evidence."
TYPED_TERM = "maintenance access route"
TYPED_LEAK = "The maintenance access route appears ahead."
TYPED_COMMAND = "Look for a maintenance access route into the facility."


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class _LegacyRejectionProvider:
    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.calls = 0
        self.rejections: list[str] = []

    def __call__(self, _command: str) -> dict[str, object]:
        text = self.texts[self.calls]
        self.calls += 1
        return {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []}

    def note_rejection(self, code: str | None) -> None:
        self.rejections.append(code or "")


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


def _item_facts_engine_with_transport(
    monkeypatch: pytest.MonkeyPatch, *script: object
) -> tuple[RuntimeEngine, RuntimeState, list[str], ItemFactsProvider]:
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
        if response == "itemfacts":
            return _Response({"refers": [], "same_as": {}})
        return _Response({"narration": json.dumps(_proposal(response))})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )
    capture = WorldCapture(provider, lambda _state, _questions: None)
    return RuntimeEngine(state, provider, capture=capture), state, prompts, provider


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


def test_budget_itemfacts_guard_retry_reaches_clean_reply_and_sanitized_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, state, prompts, provider = _item_facts_engine_with_transport(monkeypatch, "itemfacts", LEAK, CLEAN)

    result = engine.turn(COMMAND)

    assert result.segments[0].text == CLEAN
    assert provider.request_count == 3
    assert sum(system != _MATCH_SYSTEM for system in prompts) == 2
    assert state.turn_index == 1
    assert state.last_turn_delivery.guard_retry_used is True
    assert "Your last reply named something the player has not met yet." in prompts[2]
    assert "Rebecca's secured office" not in "\n".join(prompts)


def test_budget_item_facts_guard_cap_survives_match_and_restores_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, state, prompts, provider = _item_facts_engine_with_transport(monkeypatch, "itemfacts", LEAK, LEAK)
    before = state.snapshot()

    with pytest.raises(ProposalValidationError) as caught:
        engine.turn(COMMAND)

    assert caught.value.code == "narration_known_term_leak"
    assert provider.request_count == 3
    assert sum(system != _MATCH_SYSTEM for system in prompts) == 2
    assert state.snapshot() == before


def test_budget_item_facts_counter_exhaustion_fails_closed_without_narration_budget_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _engine, _state, _prompts, provider = _item_facts_engine_with_transport(
        monkeypatch, "itemfacts", "itemfacts", "itemfacts"
    )
    provider.begin_turn()

    provider._request_item_facts({"system": "match", "user": "Search the desk."})
    provider._request_item_facts({"system": "match", "user": "Search the desk."})
    with pytest.raises(NarrationProviderError) as caught:
        provider._request_item_facts({"system": "match", "user": "Search the desk."})

    assert caught.value.error_code == "ITEM_FACTS_REQUEST_BUDGET_EXHAUSTED"
    assert provider.request_budget_remaining() == 2
    assert provider.item_facts_request_budget_remaining() == 0
    provider.end_turn()


def test_budget_item_facts_begin_turn_resets_both_counters_and_sanitized_guard_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _engine, _state, _prompts, provider = _item_facts_engine_with_transport(monkeypatch, "itemfacts", CLEAN)

    provider.begin_turn()
    provider._request_item_facts({"system": "match", "user": "Search the desk."})
    provider._request({"system": "narration", "user": "Search the desk."})
    assert provider.item_facts_request_budget_remaining() == 1
    assert provider.request_budget_remaining() == 1

    provider.begin_turn()

    assert provider.item_facts_request_budget_remaining() == 2
    assert provider.request_budget_remaining() == 2
    provider.end_turn()


def test_budget_item_facts_guard_malformed_recovery_stays_at_two_narration_sends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, state, _prompts = _engine_with_transport(monkeypatch, "malformed", LEAK)
    before = state.snapshot()

    with pytest.raises(ProposalValidationError) as caught:
        engine.turn(COMMAND)

    assert caught.value.code == "narration_known_term_leak"
    assert engine.provider.request_count == 2
    assert state.snapshot() == before


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


def test_budget_guard_typed_term_feedback_names_player_phrase(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, _state, prompts = _engine_with_transport(monkeypatch, TYPED_LEAK, CLEAN)

    engine.turn(TYPED_COMMAND)

    note = (
        f'The player wrote "{TYPED_TERM}". '
        "Do not use that exact phrase in your reply. "
        "Describe what happens in other words."
    )
    assert prompts[1].count(TYPED_TERM) == 1
    assert note in prompts[1]


def test_budget_guard_typed_term_feedback_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, _state, prompts = _engine_with_transport(monkeypatch, TYPED_LEAK, CLEAN)

    engine.turn("LOOK FOR A MAINTENANCE ACCESS ROUTE INTO THE FACILITY.")

    assert f'The player wrote "{TYPED_TERM}".' in prompts[1]


def test_budget_guard_typed_term_inside_longer_word_stays_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, _state, prompts = _engine_with_transport(monkeypatch, TYPED_LEAK, CLEAN)

    engine.turn("Look for a maintenance access routekeeper into the facility.")

    assert TYPED_TERM not in prompts[1]


def test_budget_guard_sanitized_typed_note_is_cleared_after_retry_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, _state, prompts = _engine_with_transport(monkeypatch, TYPED_LEAK, CLEAN, CLEAN)

    engine.turn(TYPED_COMMAND)
    engine.provider(TYPED_COMMAND)

    assert f'The player wrote "{TYPED_TERM}".' in prompts[1]
    assert f'The player wrote "{TYPED_TERM}".' not in prompts[2]


def test_budget_guard_retry_supports_provider_without_optional_typed_argument() -> None:
    state = _scene_2c_state()
    provider = _LegacyRejectionProvider(LEAK, CLEAN)

    result = RuntimeEngine(state, provider).turn(COMMAND)

    assert result.segments[0].text == CLEAN
    assert provider.calls == 2
    assert provider.rejections == ["narration_known_term_leak"]


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
