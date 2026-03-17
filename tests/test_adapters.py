from __future__ import annotations

import io
import urllib.error

import pytest

from storygame.engine.parser import parse_command
from storygame.engine.world import build_default_state
from storygame.llm.adapters import CloudflareWorkersAIAdapter, OllamaAdapter, OpenAIAdapter, describe_prompt
from storygame.llm.context import build_narration_context


def _build_context():
    state = build_default_state(seed=11)
    return build_narration_context(state, parse_command("look"), "hook")


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_openai_adapter_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    context = _build_context()
    adapter = OpenAIAdapter()
    with pytest.raises(RuntimeError, match="requires OPENAI_API_KEY"):
        adapter.generate(context)


def test_openai_adapter_http_error_is_wrapped(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    context = _build_context()

    def _fake_urlopen(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "https://api.openai.com",
            500,
            "failure",
            None,
            io.BytesIO(b'{"error":"boom"}'),
        )

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OpenAIAdapter()
    with pytest.raises(RuntimeError, match="OpenAI API request failed: 500"):
        adapter.generate(context)


def test_openai_adapter_bad_payload_shape(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse("{}")

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OpenAIAdapter()
    with pytest.raises(RuntimeError, match="OpenAI API response missing expected message content"):
        adapter.generate(context)


def test_ollama_adapter_fallback_to_generate(monkeypatch):
    context = _build_context()
    calls: list[str] = []

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        calls.append(request.full_url)
        if request.full_url.endswith("/api/chat"):
            raise urllib.error.HTTPError(
                request.full_url,
                404,
                "not found",
                None,
                io.BytesIO(b'{"error":"not_found"}'),
            )
        return _FakeResponse('{"response":"Fallback response from generate endpoint."}')

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    adapter = OllamaAdapter(base_url="http://localhost:11434/api/chat")
    narration = adapter.generate(context)

    assert narration == "Fallback response from generate endpoint."
    assert any(url.endswith("/api/chat") for url in calls)
    assert any(url.endswith("/api/generate") for url in calls)


def test_ollama_adapter_unexpected_shape_raises(monkeypatch):
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse('{"message":{"role":"assistant"}}')

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat",),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Ollama API response missing expected message content"):
        adapter.generate(context)


def test_ollama_adapter_urls_exhausted_with_url_error(monkeypatch):
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        raise urllib.error.URLError("down")

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat",),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Ollama API request failed across endpoints"):
        adapter.generate(context)


def test_openai_adapter_url_error_is_wrapped(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    context = _build_context()

    def _fake_urlopen(*_args, **_kwargs):
        raise urllib.error.URLError("no route")

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OpenAIAdapter()
    with pytest.raises(RuntimeError, match="Cannot reach OpenAI endpoint. Check OPENAI_BASE_URL and network."):
        adapter.generate(context)


def test_openai_adapter_unexpected_exception_is_wrapped(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    context = _build_context()

    def _fake_urlopen(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OpenAIAdapter()
    with pytest.raises(RuntimeError, match="OpenAI API request failed."):
        adapter.generate(context)


def test_ollama_adapter_non_retriable_http_error_raises(monkeypatch):
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "bad request",
            None,
            io.BytesIO(b'{"error":"bad"}'),
        )

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat",),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Ollama API request failed: 400"):
        adapter.generate(context)


def test_ollama_adapter_retries_after_url_error_then_succeeds(monkeypatch):
    context = _build_context()
    calls: list[str] = []

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        calls.append(request.full_url)
        if request.full_url.endswith("/api/chat"):
            raise urllib.error.URLError("down")
        return _FakeResponse('{"response":"Recovered via secondary endpoint."}')

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat", "http://localhost:11434/api/generate"),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    narration = adapter.generate(context)

    assert narration == "Recovered via secondary endpoint."
    assert len(calls) == 2


def test_ollama_adapter_retries_after_timeout_error(monkeypatch):
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        if request.full_url.endswith("/api/chat"):
            raise TimeoutError("timed out")
        return _FakeResponse('{"response":"Recovered after timeout."}')

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat", "http://localhost:11434/api/generate"),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    narration = adapter.generate(context)

    assert narration == "Recovered after timeout."


def test_ollama_adapter_timeout_error_stops_and_reports(monkeypatch):
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        raise TimeoutError("timed out")

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat",),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Ollama API request failed across endpoints"):
        adapter.generate(context)


def test_ollama_adapter_socket_timeout_retries(monkeypatch):
    context = _build_context()

    class _AdapterSocketTimeout(Exception):
        pass

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        raise _AdapterSocketTimeout("socket timed out")

    monkeypatch.setattr(
        "storygame.llm.adapters.socket.timeout",
        _AdapterSocketTimeout,
    )

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat", "http://localhost:11434/api/generate"),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Ollama API request failed across endpoints"):
        adapter.generate(context)


def test_ollama_adapter_socket_timeout_stops_and_reports(monkeypatch):
    context = _build_context()

    class _AdapterSocketTimeout(Exception):
        pass

    first_call = True

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        nonlocal first_call
        if first_call:
            first_call = False
            raise _AdapterSocketTimeout("socket timed out")
        return _FakeResponse('{"response":"Recovered after socket timeout."}')

    monkeypatch.setattr("storygame.llm.adapters.socket.timeout", _AdapterSocketTimeout)
    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: (
            "http://localhost:11434/api/chat",
            "http://localhost:11434/api/generate",
        ),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    narration = adapter.generate(context)

    assert narration == "Recovered after socket timeout."


def test_ollama_adapter_general_exception_is_wrapped(monkeypatch):
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        raise ValueError("bad")

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat",),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Ollama API request failed with ValueError"):
        adapter.generate(context)


def test_ollama_adapter_parses_choices_payload(monkeypatch):
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse('{"choices":[{"message":{"content":"Told through choices."}}]}')

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat",),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    narration = adapter.generate(context)

    assert narration == "Told through choices."


def test_ollama_adapter_unexpected_choices_shape_is_wrapped(monkeypatch):
    context = _build_context()

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse('{"choices":[{"delta":{"content":"missing"}}]}')

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: ("http://localhost:11434/api/chat",),
    )
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = OllamaAdapter(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Ollama API response had unexpected shape."):
        adapter.generate(context)


def test_ollama_adapter_no_endpoints_reports_no_endpoint_diagnostics(monkeypatch):
    context = _build_context()

    monkeypatch.setattr(
        "storygame.llm.adapters.OllamaAdapter._normalized_endpoints",
        lambda self: tuple(),
    )
    adapter = OllamaAdapter(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Ollama API request failed with no endpoint diagnostics."):
        adapter.generate(context)


def test_ollama_adapter_normalized_endpoint_variants():
    chat_adapter = OllamaAdapter(base_url="http://localhost:11434/api/chat")
    chat_endpoints = chat_adapter._normalized_endpoints()
    assert any(endpoint.endswith("/api/chat") for endpoint in chat_endpoints)
    assert any(endpoint.endswith("/api/generate") for endpoint in chat_endpoints)

    generate_adapter = OllamaAdapter(base_url="http://localhost:11434/api/generate")
    generate_endpoints = generate_adapter._normalized_endpoints()
    assert any(endpoint.endswith("/api/generate") for endpoint in generate_endpoints)
    assert any(endpoint.endswith("/api/chat") for endpoint in generate_endpoints)

    v1_adapter = OllamaAdapter(base_url="http://localhost:11434/v1/chat/completions")
    v1_endpoints = v1_adapter._normalized_endpoints()
    assert any(endpoint.endswith("/api/chat") for endpoint in v1_endpoints)

    example_adapter = OllamaAdapter(base_url="http://example.com")
    example_endpoints = example_adapter._normalized_endpoints()
    assert any(endpoint.endswith("/api/chat") for endpoint in example_endpoints)
    assert all("localhost" not in endpoint and "127.0.0.1" not in endpoint for endpoint in example_endpoints)


def test_describe_prompt_wraps_prompt_builder():
    text = describe_prompt(_build_context())
    assert isinstance(text, str)
    assert "Narrate only" in text


def test_cloudflare_adapter_requires_worker_url(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    adapter = CloudflareWorkersAIAdapter(worker_url=None)
    with pytest.raises(RuntimeError, match="requires CLOUDFLARE_WORKER_URL"):
        adapter.generate(_build_context())


def test_cloudflare_adapter_success_parses_narration(monkeypatch):
    observed: dict[str, object] = {}

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        observed["user_agent"] = request.headers.get("User-agent")
        return _FakeResponse('{"narration":"Cloudflare narration response.","model":"demo-model"}')

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    adapter = CloudflareWorkersAIAdapter(worker_url="https://demo.example.workers.dev/api/narrate", token="t")
    assert adapter.generate(_build_context()) == "Cloudflare narration response."
    assert observed["user_agent"] == "FreytagForgeDemo/1.0"


def test_cloudflare_adapter_trims_env_worker_url_and_token(monkeypatch):
    observed: dict[str, object] = {}

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        observed["url"] = request.full_url
        observed["auth"] = request.headers.get("Authorization")
        observed["user_agent"] = request.headers.get("User-agent")
        observed["timeout"] = timeout
        return _FakeResponse('{"narration":"Cloudflare narration response."}')

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", " https://demo.example.workers.dev/api/narrate ")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", " secret-token ")
    monkeypatch.setenv("CLOUDFLARE_TIMEOUT", "7.5")
    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)

    adapter = CloudflareWorkersAIAdapter()
    assert adapter.generate(_build_context()) == "Cloudflare narration response."
    assert observed == {
        "url": "https://demo.example.workers.dev/api/narrate",
        "auth": "Bearer secret-token",
        "user_agent": "FreytagForgeDemo/1.0",
        "timeout": 7.5,
    }


def test_cloudflare_adapter_maps_quota_http_error(monkeypatch):
    def _fake_urlopen(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "https://demo.example.workers.dev/api/narrate",
            429,
            "Too Many Requests",
            None,
            io.BytesIO(b'{"code":"AI_QUOTA_EXCEEDED","message":"quota"}'),
        )

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    adapter = CloudflareWorkersAIAdapter(worker_url="https://demo.example.workers.dev/api/narrate")
    with pytest.raises(RuntimeError, match="AI_QUOTA_EXCEEDED"):
        adapter.generate(_build_context())


def test_cloudflare_adapter_retries_transient_http_5xx_then_succeeds(monkeypatch):
    attempts = {"count": 0}

    def _fake_urlopen(*_args, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise urllib.error.HTTPError(
                "https://demo.example.workers.dev/api/narrate",
                503,
                "Service Unavailable",
                None,
                io.BytesIO(b'{"code":"AI_UPSTREAM_ERROR","message":"temporary"}'),
            )
        return _FakeResponse('{"narration":"Recovered narration."}')

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    monkeypatch.setattr("storygame.llm.adapters.time.sleep", lambda _seconds: None)

    adapter = CloudflareWorkersAIAdapter(
        worker_url="https://demo.example.workers.dev/api/narrate",
        retries=1,
        retry_backoff_ms=0,
    )
    assert adapter.generate(_build_context()) == "Recovered narration."
    assert attempts["count"] == 2


def test_cloudflare_adapter_retries_url_error_then_succeeds(monkeypatch):
    attempts = {"count": 0}

    def _fake_urlopen(*_args, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise urllib.error.URLError("temporary network down")
        return _FakeResponse('{"narration":"Recovered narration."}')

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    monkeypatch.setattr("storygame.llm.adapters.time.sleep", lambda _seconds: None)

    adapter = CloudflareWorkersAIAdapter(
        worker_url="https://demo.example.workers.dev/api/narrate",
        retries=1,
        retry_backoff_ms=0,
    )
    assert adapter.generate(_build_context()) == "Recovered narration."
    assert attempts["count"] == 2


def test_cloudflare_adapter_does_not_retry_http_403(monkeypatch):
    attempts = {"count": 0}

    def _fake_urlopen(*_args, **_kwargs):
        attempts["count"] += 1
        raise urllib.error.HTTPError(
            "https://demo.example.workers.dev/api/narrate",
            403,
            "Forbidden",
            None,
            io.BytesIO(b"error code: 1010"),
        )

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    monkeypatch.setattr("storygame.llm.adapters.time.sleep", lambda _seconds: None)

    adapter = CloudflareWorkersAIAdapter(
        worker_url="https://demo.example.workers.dev/api/narrate",
        retries=2,
        retry_backoff_ms=0,
    )
    with pytest.raises(RuntimeError, match="403"):
        adapter.generate(_build_context())
    assert attempts["count"] == 1


def test_cloudflare_adapter_wraps_url_error(monkeypatch):
    def _fake_urlopen(*_args, **_kwargs):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    adapter = CloudflareWorkersAIAdapter(worker_url="https://demo.example.workers.dev/api/narrate")
    with pytest.raises(RuntimeError, match="Cannot reach Cloudflare Worker endpoint"):
        adapter.generate(_build_context())
