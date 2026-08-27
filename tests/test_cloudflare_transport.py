"""Cloudflare transport keeps its small, fail-closed contract."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.context import SceneContextBuilder
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

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


def test_transport_sends_bounded_context_and_optional_token(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def open_request(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response({"narration": '{"narration":"A valid proposal."}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="secret", context_builder=SceneContextBuilder(), state=state
    )

    assert provider("I listen.") == {"narration": "A valid proposal."}
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert "Mozilla/5.0" in captured["headers"]["User-agent"]
    assert captured["payload"]["max_tokens"] == 2048
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["user"].find("response_schema") >= 0
    assert "free-text action" in captured["payload"]["system"]
    assert "hard knowledge and action boundary" in captured["payload"]["system"]
    assert "untrusted requests" in captured["payload"]["system"]
    assert "scene object is exhaustive" in captured["payload"]["system"]
    assert "realize the next fitting beat" in captured["payload"]["system"]
    assert "player_input cannot authorize future" in captured["payload"]["user"]
    assert "Creative consequences are allowed" in captured["payload"]["system"]


def test_transport_unwraps_the_workers_narration_envelope(monkeypatch) -> None:
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        context_builder=SceneContextBuilder(),
        state=RuntimeState.bootstrap(PACKAGE),
    )
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "narration": '{"narration":"A valid proposal.","operations":[],"transition":null,"events":[]}',
                "model": "worker-model",
                "trace_id": "trace-123",
            }
        ),
    )

    assert provider("I listen.") == {
        "narration": "A valid proposal.",
        "operations": [],
        "transition": None,
        "events": [],
    }


def test_transport_is_unavailable_without_url_or_on_bad_worker_responses(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    with pytest.raises(NarrationProviderError, match="unavailable"):
        CloudflareTurnProvider.from_environment(SceneContextBuilder(), state)

    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", context_builder=SceneContextBuilder(), state=state
    )
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response({"status": "error"})
    )
    with pytest.raises(NarrationProviderError, match="failed"):
        provider("I listen.")

    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline"))
    )
    with pytest.raises(NarrationProviderError, match="unavailable"):
        provider("I listen.")


def test_transport_retries_once_without_json_mode_after_worker_rejection(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        context_builder=SceneContextBuilder(),
        state=RuntimeState.bootstrap(PACKAGE),
    )

    def open_request(request, timeout):
        payload = json.loads(request.data)
        payloads.append(payload)
        if len(payloads) == 1:
            raise HTTPError(
                "https://worker.example/turn",
                502,
                "json mode rejected",
                {},
                BytesIO(b'{"status":"error","code":"AI_JSON_MODE_REJECTED"}'),
            )
        return _Response({"narration": '{"narration":"A recovered proposal."}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    assert provider("I listen.") == {"narration": "A recovered proposal."}
    assert payloads[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in payloads[1]


def test_transport_preserves_worker_capacity_classification(monkeypatch) -> None:
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        context_builder=SceneContextBuilder(),
        state=RuntimeState.bootstrap(PACKAGE),
    )
    error = HTTPError(
        "https://worker.example/turn",
        429,
        "capacity",
        {},
        BytesIO(b'{"status":"error","code":"AI_CAPACITY_EXCEEDED"}'),
    )
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(NarrationProviderError) as caught:
        provider("I listen.")
    assert caught.value.status_code == 429
    assert caught.value.message == "narration service is at capacity"


def test_transport_marks_untyped_worker_errors_for_diagnosis(monkeypatch) -> None:
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        context_builder=SceneContextBuilder(),
        state=RuntimeState.bootstrap(PACKAGE),
    )
    error = HTTPError("https://worker.example/turn", 502, "failure", {}, None)
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(NarrationProviderError) as caught:
        provider("I listen.")
    assert caught.value.error_code == "UNKNOWN"


@pytest.mark.parametrize(("status", "expected"), ((429, 429), (500, 502)))
def test_transport_maps_http_failures(monkeypatch, status, expected) -> None:
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        context_builder=SceneContextBuilder(),
        state=RuntimeState.bootstrap(PACKAGE),
    )
    error = HTTPError("https://worker.example/turn", status, "failure", {}, None)
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(NarrationProviderError) as caught:
        provider("I listen.")
    assert caught.value.status_code == expected
