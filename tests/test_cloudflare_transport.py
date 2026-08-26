"""Cloudflare transport keeps its small, fail-closed contract."""

from __future__ import annotations

import json
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
        return _Response({"narration": "A valid proposal."})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="secret", context_builder=SceneContextBuilder(), state=state
    )

    assert provider("I listen.") == {"narration": "A valid proposal."}
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["user"].find("scene_context") >= 0


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
