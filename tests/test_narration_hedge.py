"""Narration hedging keeps one logical request and one winning reply."""

from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _payload() -> dict[str, object]:
    return {"system": "system", "user": "user"}


def _provider() -> CloudflareTurnProvider:
    return CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )


def _item_facts_provider() -> ItemFactsProvider:
    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
        item_facts={},
        mode="single_call",
    )


def _reply(text: str) -> bytes:
    return json.dumps(
        {
            "segments": [{"kind": "narration", "text": text}],
            "lantern": {"place": "the desk"},
        }
    ).encode()


def _slow_then_fast(first: bytes, second: bytes, delay: float = 0.08):
    calls: list[int] = []
    lock = Lock()

    def send_http(_wire_payload: dict[str, object]) -> bytes:
        with lock:
            call_number = len(calls)
            calls.append(call_number)
        if call_number == 0:
            time.sleep(delay)
            return first
        return second

    return calls, send_http


def _loser_send_http(calls: list[int], lock: Lock, late_failure: bool):
    def send_http(_wire_payload: dict[str, object]) -> bytes:
        with lock:
            call_number = len(calls)
            calls.append(call_number)
        if call_number == 0:
            time.sleep(0.07)
            if late_failure:
                raise RuntimeError("loser failed")
            return _reply("late")
        return _reply("winner")

    return send_http


@pytest.mark.parametrize("provider_factory", [_provider, _item_facts_provider])
def test_fast_reply_sends_one_http_request(monkeypatch, provider_factory) -> None:
    provider = provider_factory()
    calls: list[dict[str, object]] = []

    def send_http(wire_payload: dict[str, object]) -> bytes:
        calls.append(wire_payload)
        return _reply("fast")

    monkeypatch.setattr(provider, "_send_http", send_http)
    monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", "0.02")

    result = provider._request_allowing_one_transient_retry(_payload())

    assert result["segments"] == [{"kind": "narration", "text": "fast"}]
    assert len(calls) == 1
    assert provider.request_count == 1
    assert provider.last_narration_hedge is not None
    assert provider.last_narration_hedge.hedge_fired is False


def test_slow_narration_hedges_in_base_provider(monkeypatch) -> None:
    provider = _provider()
    provider.begin_turn()
    calls, send_http = _slow_then_fast(_reply("late"), _reply("hedge"))
    monkeypatch.setattr(provider, "_send_http", send_http)
    monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", "0.02")

    result = provider._request_allowing_one_transient_retry(_payload())
    time.sleep(0.08)

    assert result["segments"] == [{"kind": "narration", "text": "hedge"}]
    assert len(calls) == 2
    assert provider.request_count == 1
    assert provider._turn_request_count == 1
    assert provider.last_narration_hedge is not None
    assert provider.last_narration_hedge.hedge_fired is True
    assert provider.last_narration_hedge.winner == "hedge"


def test_slow_narration_hedges_before_item_facts_post_processing(monkeypatch) -> None:
    provider = _item_facts_provider()
    provider.begin_turn()
    calls, send_http = _slow_then_fast(_reply("late"), _reply("hedge"))
    monkeypatch.setattr(provider, "_send_http", send_http)
    monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", "0.02")

    result = provider._request_allowing_one_transient_retry(_payload())
    time.sleep(0.08)

    assert result == {"segments": [{"kind": "narration", "text": "hedge"}]}
    assert len(calls) == 2
    assert provider.request_count == 1
    assert provider._turn_request_count == 1
    assert provider.item_facts_lifted == 1
    assert provider.item_facts_reply_keys == {"place": 1, "contents": 0, "under": 0}
    assert provider._pending_item_facts == {"lantern": {"place": "the desk"}}


def test_loser_late_result_or_exception_is_swallowed(monkeypatch) -> None:
    for late_failure in (False, True):
        provider = _item_facts_provider()
        calls: list[int] = []
        lock = Lock()

        monkeypatch.setattr(provider, "_send_http", _loser_send_http(calls, lock, late_failure))
        monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", "0.01")

        result = provider._request_allowing_one_transient_retry(_payload())
        time.sleep(0.08)

        assert result == {"segments": [{"kind": "narration", "text": "winner"}]}
        assert len(calls) == 2
        assert provider.item_facts_lifted == 1


def test_both_slow_replies_raise_the_transport_timeout(monkeypatch) -> None:
    provider = _provider()
    calls = 0

    def send_http(_wire_payload: dict[str, object]) -> bytes:
        nonlocal calls
        calls += 1
        time.sleep(0.3)
        return _reply("too late")

    monkeypatch.setattr(provider, "_send_http", send_http)
    monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", "0.02")
    monkeypatch.setenv("CLOUDFLARE_TIMEOUT", "0.06")
    started = time.monotonic()

    with pytest.raises(TimeoutError):
        provider._request_allowing_one_transient_retry(_payload())

    assert time.monotonic() - started < 0.15
    assert calls == 2
    assert provider.request_count == 1


def test_answered_http_error_is_not_hedged(monkeypatch) -> None:
    provider = _item_facts_provider()
    calls = 0
    error = HTTPError(
        "https://worker.example/turn",
        503,
        "busy",
        {},
        BytesIO(b'{"detail":"busy"}'),
    )

    def send_http(_wire_payload: dict[str, object]) -> bytes:
        nonlocal calls
        calls += 1
        raise error

    monkeypatch.setattr(provider, "_send_http", send_http)
    monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", "0.02")

    with pytest.raises(HTTPError) as raised:
        provider._request_allowing_one_transient_retry(_payload())

    assert raised.value is error
    assert calls == 1
    assert provider.request_count == 1


@pytest.mark.parametrize("provider_factory", [_provider, _item_facts_provider])
@pytest.mark.parametrize("configured_delay", ["0.02", "0"])
def test_budgets_and_counters_match_with_hedging_on_or_off(monkeypatch, provider_factory, configured_delay) -> None:
    provider = provider_factory()
    provider.begin_turn()
    calls = 0

    def send_http(_wire_payload: dict[str, object]) -> bytes:
        nonlocal calls
        calls += 1
        return _reply("same")

    monkeypatch.setattr(provider, "_send_http", send_http)
    monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", configured_delay)

    provider._request_allowing_one_transient_retry(_payload())

    assert calls == 1
    assert (provider.request_count, provider._turn_request_count, provider.recovery_count) == (1, 1, 0)
    assert provider.request_budget_remaining() == 1


def test_zero_narration_delay_restores_single_request(monkeypatch) -> None:
    provider = _item_facts_provider()
    calls = 0

    def send_http(_wire_payload: dict[str, object]) -> bytes:
        nonlocal calls
        calls += 1
        return _reply("single")

    monkeypatch.setattr(provider, "_send_http", send_http)
    monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", "0")

    provider._request_allowing_one_transient_retry(_payload())

    assert calls == 1
    assert provider.last_narration_hedge is not None
    assert provider.last_narration_hedge.hedge_fired is False


def test_malformed_reply_then_recovery_uses_one_recovery_request(monkeypatch) -> None:
    provider = _item_facts_provider()
    calls = 0

    def send_http(_wire_payload: dict[str, object]) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 1:
            return b"not json"
        return _reply("recovered")

    monkeypatch.setattr(provider, "_send_http", send_http)
    monkeypatch.setenv("FREYTAG_HEDGE_NARRATION_S", "0.02")
    provider.begin_turn()

    result = provider("Listen.")

    assert result["segments"][0]["text"] == "recovered"
    assert calls == 2
    assert provider.recovery_count == 1
    assert provider.request_count == 2
    assert provider._turn_request_count == 2
