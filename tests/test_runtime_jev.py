"""Jev client uses the Worker endpoint and fails closed."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError

from storygame.runtime.cloudflare import BROWSER_USER_AGENT
from storygame.runtime.jev import JevClient, noul_yes


class _Response:
    def __init__(self, body: object) -> None:
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_jev_client_posts_to_jev_path() -> None:
    captured: dict[str, object] = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response({"answers": {"safe": {"type": "noul", "noul": 0.8}}})

    client = JevClient("https://worker.example/", "secret", opener=opener)
    assert client.ask({"scene": "hall"}, {"safe": "Is it safe?"}) == {"safe": {"type": "noul", "noul": 0.8}}
    assert str(captured["url"]).endswith("/jev")
    assert captured["body"] == {"input": {"state": {"scene": "hall"}, "questions": {"safe": "Is it safe?"}}}
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["headers"]["User-agent"] == BROWSER_USER_AGENT


def test_jev_client_records_model_and_status_on_success() -> None:
    def opener(*_args, **_kwargs):
        return _Response({"answers": {"q": {"noul": 0.8}}, "model": "jev-test-1"})

    client = JevClient("https://worker.example", "", opener=opener)

    assert client.ask({}, {"q": "?"}) == {"q": {"noul": 0.8}}
    assert client.last_model == "jev-test-1"
    assert client.last_status == 200


def test_jev_client_leaves_model_unset_when_body_has_no_model() -> None:
    def opener(*_args, **_kwargs):
        return _Response({"answers": {"q": {"noul": 0.8}}})

    client = JevClient("https://worker.example", "", opener=opener)

    assert client.ask({}, {"q": "?"}) == {"q": {"noul": 0.8}}
    assert client.last_model is None
    assert client.last_status == 200


def test_jev_client_leaves_model_unset_for_error_body() -> None:
    def opener(*_args, **_kwargs):
        return _Response({"status": "error", "model": "jev-test-1"})

    client = JevClient("https://worker.example", "", opener=opener)

    assert client.ask({}, {"q": "?"}) is None
    assert client.last_model is None
    assert client.last_status == 200


def test_jev_client_records_http_error_status() -> None:
    def opener(*_args, **_kwargs):
        raise HTTPError("url", 429, "rate limited", {}, None)

    client = JevClient("https://worker.example", "", opener=opener)

    assert client.ask({}, {"q": "?"}) is None
    assert client.last_model is None
    assert client.last_status == 429


def test_jev_client_success_resets_previous_failure_status() -> None:
    def failing_opener(*_args, **_kwargs):
        raise HTTPError("url", 429, "rate limited", {}, None)

    def successful_opener(*_args, **_kwargs):
        return _Response({"answers": {"q": {"noul": 0.8}}, "model": "jev-test-1"})

    client = JevClient("https://worker.example", "", opener=failing_opener)

    assert client.ask({}, {"q": "?"}) is None
    assert client.last_status == 429

    client.opener = successful_opener
    assert client.ask({}, {"q": "?"}) == {"q": {"noul": 0.8}}
    assert client.last_model == "jev-test-1"
    assert client.last_status == 200


def test_jev_client_returns_none_on_error() -> None:
    failures = [
        lambda *_args, **_kwargs: (_ for _ in ()).throw(HTTPError("url", 500, "bad", {}, None)),
        lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")),
        lambda *_args, **_kwargs: _Response(b"not json"),
        lambda *_args, **_kwargs: _Response({"status": "error"}),
        lambda *_args, **_kwargs: _Response({}),
    ]
    client = JevClient("https://worker.example", "", opener=failures[0])
    for opener in failures:
        client.opener = opener
        assert client.ask({}, {"q": "?"}) is None
    assert client.request_count == len(failures)


def test_jev_client_returns_none_without_url() -> None:
    client = JevClient("", "secret")
    assert client.ask({}, {"q": "?"}) is None
    assert client.request_count == 1


def test_noul_yes_threshold() -> None:
    assert noul_yes({"type": "noul", "noul": 0.51}) is True
    assert noul_yes({"type": "noul", "noul": 0.5}) is False
    assert noul_yes({"type": "noul", "noul": 0.2}) is False
    assert noul_yes({"type": "noul"}) is None
    assert noul_yes({"type": "noul", "noul": True}) is None
    assert noul_yes({"type": "noul", "noul": "0.8"}) is None
