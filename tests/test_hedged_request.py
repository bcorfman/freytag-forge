"""Hermetic tests for request hedging and its runtime wiring."""

from __future__ import annotations

import json
import time
from threading import local
from urllib.error import HTTPError

import pytest

from storygame.runtime import cloudflare, jev
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.hedged_request import HedgedResult, configured_hedge_delay, hedged_call
from storygame.runtime.jev import JevClient


class _Response:
    status = 200

    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_fast_primary_returns_without_a_hedge() -> None:
    calls = 0

    def send() -> str:
        nonlocal calls
        calls += 1
        return "primary"

    result = hedged_call(send, delay_s=0.05, timeout_s=0.3)

    assert result == HedgedResult("primary", False, "primary")
    assert calls == 1


def test_slow_primary_and_fast_hedge_returns_the_hedge() -> None:
    calls = 0

    def send() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            time.sleep(0.12)
            return "primary"
        time.sleep(0.01)
        return "hedge"

    result = hedged_call(send, delay_s=0.03, timeout_s=0.25)

    assert result == HedgedResult("hedge", True, "hedge")
    assert calls == 2


def test_both_slow_attempts_raise_within_the_total_timeout() -> None:
    calls = 0

    def send() -> str:
        nonlocal calls
        calls += 1
        time.sleep(0.3)
        return "late"

    started = time.monotonic()
    with pytest.raises(TimeoutError):
        hedged_call(send, delay_s=0.03, timeout_s=0.1)

    assert time.monotonic() - started < 0.2
    assert calls == 2


def test_answered_http_error_is_not_hedged() -> None:
    calls = 0
    error = HTTPError("https://worker.example", 503, "busy", {}, None)

    def send() -> str:
        nonlocal calls
        calls += 1
        raise error

    with pytest.raises(HTTPError) as caught:
        hedged_call(send, delay_s=0.05, timeout_s=0.3)

    assert caught.value is error
    assert calls == 1


def test_primary_failure_before_delay_is_not_hedged() -> None:
    calls = 0
    error = RuntimeError("offline")

    def send() -> str:
        nonlocal calls
        calls += 1
        raise error

    with pytest.raises(RuntimeError) as caught:
        hedged_call(send, delay_s=0.05, timeout_s=0.3)

    assert caught.value is error
    assert calls == 1


def test_loser_exception_is_swallowed() -> None:
    calls = 0

    def send() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            time.sleep(0.08)
            return "primary"
        time.sleep(0.01)
        raise RuntimeError("hedge lost")

    result = hedged_call(send, delay_s=0.02, timeout_s=0.2)

    assert result == HedgedResult("primary", True, "primary")


def test_zero_environment_delay_disables_hedging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FREYTAG_HEDGE_DELAY_S", "0")
    calls = 0

    def send() -> str:
        nonlocal calls
        calls += 1
        return "primary"

    result = hedged_call(send, delay_s=configured_hedge_delay(2.5), timeout_s=0.3)

    assert result == HedgedResult("primary", False, "primary")
    assert calls == 1


def _provider_for_transport() -> CloudflareTurnProvider:
    provider = object.__new__(CloudflareTurnProvider)
    provider.worker_url = "https://worker.example/turn"
    provider.token = ""
    provider.request_count = 0
    provider._turn_request_count = 0
    provider._turn_item_facts_request_count = 0
    provider._request_budget_reservation = local()
    provider.reply_keys_dropped = {}
    provider.last_item_facts_hedge = None
    return provider


def test_item_facts_uses_the_helper_and_keeps_logical_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider_for_transport()
    sends = 0

    def request(_provider: CloudflareTurnProvider, payload: dict[str, object]) -> object:
        nonlocal sends
        sends += 1
        assert payload["__freytag_request_budget"] == "item_facts"
        return {"same_as": {}}

    def helper(send, *, delay_s, timeout_s):
        assert delay_s == 2.5
        assert timeout_s == 20.0
        value = send()
        send()
        return HedgedResult(value, True, "hedge")

    monkeypatch.delenv("FREYTAG_HEDGE_DELAY_S", raising=False)
    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    monkeypatch.setattr(cloudflare, "hedged_call", helper)

    assert provider._request_item_facts({"system": "match", "user": "desk"}) == {"same_as": {}}
    assert sends == 2
    assert provider.request_count == 1
    assert provider._turn_item_facts_request_count == 1
    assert provider.last_item_facts_hedge.hedge_fired is True


def test_jev_post_uses_the_helper_once_logically(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def opener(_request, timeout):
        nonlocal calls
        calls += 1
        assert timeout == 15.0
        return _Response({"answers": {"safe": {"noul": 0.8}}})

    def helper(send, *, delay_s, timeout_s):
        assert delay_s == 2.5
        assert timeout_s == 15.0
        return HedgedResult(send(), True, "hedge")

    monkeypatch.delenv("FREYTAG_HEDGE_DELAY_S", raising=False)
    monkeypatch.setattr(jev, "hedged_call", helper)
    client = JevClient("https://worker.example", "", opener=opener)

    assert client.ask({}, {"safe": "?"}) == {"safe": {"noul": 0.8}}
    assert client.request_count == 1
    assert calls == 1
    assert client.last_hedge.hedge_fired is True


def test_narration_request_does_not_use_the_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider_for_transport()
    provider.last_prompt = None

    def helper(*_args, **_kwargs):
        raise AssertionError("narration must not be hedged")

    monkeypatch.setattr(cloudflare, "hedged_call", helper)
    monkeypatch.setattr(
        cloudflare,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"segments": [{"kind": "narration", "text": "Quiet."}]}),
    )

    assert provider._request({"system": "narrate", "user": "look"}) == {
        "segments": [{"kind": "narration", "text": "Quiet."}]
    }
    assert provider.request_count == 1
