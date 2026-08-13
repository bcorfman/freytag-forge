from __future__ import annotations

import io
import json
import urllib.error

import pytest

from storygame.engine.parser import parse_command
from storygame.llm.adapters import CloudflareNarrationError, CloudflareWorkersAIAdapter
from storygame.llm.context import build_narration_context
from tests.fast_fixtures import make_cached_story_state as build_default_state


class _FakeResponse:
    def __init__(self, body: str, headers: dict[str, str] | None = None) -> None:
        self._body = body.encode("utf-8")
        self.headers = {} if headers is None else headers

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _context():
    return build_narration_context(build_default_state(seed=11), parse_command("look"), "hook")


def test_cloudflare_adapter_requires_worker_url(monkeypatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    with pytest.raises(RuntimeError, match="CLOUDFLARE_WORKER_URL"):
        CloudflareWorkersAIAdapter().generate(_context())


def test_cloudflare_adapter_posts_narration_request(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def _urlopen(request, timeout):  # type: ignore[no-untyped-def]
        observed["payload"] = json.loads(request.data)
        observed["timeout"] = timeout
        return _FakeResponse('{"narration":"A measured reply follows."}', {"X-Worker-Revision": "r1"})

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _urlopen)
    adapter = CloudflareWorkersAIAdapter(worker_url="https://demo.example.workers.dev/api/narrate", token="token")
    assert adapter.generate(_context()) == "A measured reply follows."
    assert observed["payload"]
    assert adapter.worker_revision == "r1"


def test_cloudflare_adapter_retries_one_transient_failure(monkeypatch) -> None:
    calls = 0

    def _urlopen(request, timeout):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        if calls == 1:
            raise urllib.error.HTTPError(request.full_url, 503, "unavailable", {}, io.BytesIO(b"{}"))
        return _FakeResponse('{"narration":"Recovered."}')

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _urlopen)
    adapter = CloudflareWorkersAIAdapter(worker_url="https://demo.example.workers.dev/api/narrate", retry_backoff_ms=0)
    assert adapter.generate(_context()) == "Recovered."
    assert calls == 2


def test_cloudflare_adapter_fails_closed_on_bad_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "storygame.llm.adapters.urllib.request.urlopen",
        lambda *_args, **_kwargs: _FakeResponse('{"status":"error","code":"AI_REQUEST_REJECTED"}'),
    )
    adapter = CloudflareWorkersAIAdapter(worker_url="https://demo.example.workers.dev/api/narrate", retries=0)
    with pytest.raises(CloudflareNarrationError, match="AI_REQUEST_REJECTED"):
        adapter.generate(_context())
