"""Hermetic coverage for Cloudflare request timeout and retry policy."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from tests.test_recovery_budget import (
    CLEAN,
    COMMAND,
    _item_facts_engine_with_transport,
)

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _valid_response() -> _Response:
    proposal = {"segments": [{"kind": "narration", "text": "The corridor holds."}]}
    return _Response({"narration": json.dumps(proposal)})


def _provider() -> CloudflareTurnProvider:
    return CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )


def test_request_timeout_defaults_to_twenty_seconds_and_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    timeouts: list[float] = []

    def open_request(_request: object, timeout: float) -> _Response:
        timeouts.append(timeout)
        return _valid_response()

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    monkeypatch.delenv("CLOUDFLARE_TIMEOUT", raising=False)
    _provider()("Listen.")

    monkeypatch.setenv("CLOUDFLARE_TIMEOUT", "7.25")
    _provider()("Listen.")

    assert timeouts == [20.0, 7.25]


def test_timeout_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def open_request(_request: object, timeout: float) -> _Response:
        calls.append(1)
        raise TimeoutError("timed out")

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = _provider()

    with pytest.raises(NarrationProviderError) as caught:
        provider("Listen.")

    assert isinstance(caught.value.__cause__, TimeoutError)
    assert calls == [1]
    assert provider.request_count == 1


def test_urlerror_with_timeout_reason_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def open_request(_request: object, timeout: float) -> _Response:
        calls.append(1)
        raise URLError(TimeoutError("timed out"))

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = _provider()

    with pytest.raises(NarrationProviderError) as caught:
        provider("Listen.")

    assert isinstance(caught.value.__cause__, URLError)
    assert calls == [1]
    assert provider.request_count == 1


def test_urlerror_connection_failure_retries_once_and_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def open_request(_request: object, timeout: float) -> _Response:
        calls.append(1)
        if len(calls) == 1:
            raise URLError("offline")
        return _valid_response()

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = _provider()

    assert provider("Listen.")["segments"][0]["text"] == "The corridor holds."
    assert calls == [1, 1]
    assert provider.request_count == 2


def test_connection_failure_on_both_sends_raises_after_one_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def open_request(_request: object, timeout: float) -> _Response:
        calls.append(1)
        raise URLError("offline")

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = _provider()

    with pytest.raises(NarrationProviderError) as caught:
        provider("Listen.")

    assert isinstance(caught.value.__cause__, URLError)
    assert calls == [1, 1]
    assert provider.request_count == 2


def test_http_error_is_never_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    failure = HTTPError("https://worker.example/turn", 503, "unavailable", {}, None)

    def open_request(_request: object, timeout: float) -> _Response:
        calls.append(1)
        raise failure

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = _provider()

    with pytest.raises(NarrationProviderError):
        provider("Listen.")

    assert calls == [1]
    assert provider.request_count == 1


def test_engine_timeout_rolls_back_item_facts_and_next_turn_works(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, state, _prompts, provider = _item_facts_engine_with_transport(
        monkeypatch,
        "itemfacts",
        TimeoutError("timed out"),
        "itemfacts",
        CLEAN,
    )
    before = state.snapshot()

    with pytest.raises(NarrationProviderError) as caught:
        engine.turn(COMMAND)

    assert caught.value.message == "narration service is unavailable"
    assert state.snapshot() == before
    assert state.turn_index == before.turn_index
    assert state.facts == before.facts
    assert provider.request_count == 2

    result = engine.turn(COMMAND)

    assert result.segments[0].text == CLEAN
    assert state.turn_index == before.turn_index + 1
    assert provider.request_count == 4


def test_begin_turn_resets_budget_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, _state, _prompts, provider = _item_facts_engine_with_transport(
        monkeypatch,
        "itemfacts",
        TimeoutError("timed out"),
    )

    with pytest.raises(NarrationProviderError):
        engine.turn(COMMAND)

    assert provider.request_budget_remaining() == 2
    provider.begin_turn()
    assert provider.request_budget_remaining() == 2
    provider.end_turn()
