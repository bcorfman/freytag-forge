from __future__ import annotations

import json
from io import BytesIO

import pytest

from storygame.runtime.cloudflare import CloudflareTurnModel
from storygame.runtime.context import RuntimeContext
from storygame.runtime.engine import JsonModeRejected


def test_cloudflare_turn_model_requests_json_mode(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        def read(self) -> bytes:
            return b'{"narration":"{\\"narration\\":\\"Done.\\"}","model":"model-id","trace_id":"trace-id"}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def urlopen(request, timeout):
        captured["payload"] = json.loads(request.data)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    result = CloudflareTurnModel(url="https://agent.test").play_turn(RuntimeContext("v1", 1, {}), json_object=True)
    assert result == {"narration": "Done."}
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["max_tokens"] == 1024
    assert "operations must be an array" in captured["payload"]["system"]


def test_cloudflare_turn_model_strips_known_transport_metadata(monkeypatch) -> None:
    class Response:
        def read(self) -> bytes:
            return b'{"narration":"Done.","model":"model-id","trace_id":"trace-id","upstream_request_id":"request-id"}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    result = CloudflareTurnModel(url="https://agent.test").play_turn(RuntimeContext("v1", 1, {}), json_object=True)
    assert result == {"narration": "Done."}


def test_cloudflare_turn_model_maps_json_mode_rejection(monkeypatch) -> None:
    from urllib.error import HTTPError

    def urlopen(request, timeout):
        raise HTTPError(
            "https://agent.test",
            502,
            "bad",
            {},
            BytesIO(b'{"status":"error","code":"AI_JSON_MODE_REJECTED","message":"unsupported response_format"}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    with pytest.raises(JsonModeRejected):
        CloudflareTurnModel(url="https://agent.test").play_turn(RuntimeContext("v1", 1, {}), json_object=True)


def test_cloudflare_turn_model_returns_a_diagnostic_for_non_json_mode_http_error(monkeypatch) -> None:
    from urllib.error import HTTPError

    def urlopen(request, timeout):
        raise HTTPError("https://agent.test", 502, "bad", {}, BytesIO(b'{"code":"AI_UPSTREAM_ERROR"}'))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    with pytest.raises(RuntimeError, match="502.*AI_UPSTREAM_ERROR"):
        CloudflareTurnModel(url="https://agent.test").play_turn(RuntimeContext("v1", 1, {}), json_object=False)


def test_cloudflare_turn_model_sends_bearer_token_and_fails_safely(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        def read(self) -> bytes:
            return b'{"narration":"Done."}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def urlopen(request, timeout):
        captured["headers"] = dict(request.headers)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    model = CloudflareTurnModel(url="https://agent.test", token="secret")
    assert model.play_turn(RuntimeContext("v1", 1, {}), json_object=False) == {"narration": "Done."}
    assert captured["headers"]["Authorization"] == "Bearer secret"

    with pytest.raises(ValueError, match="CLOUDFLARE_WORKER_URL"):
        CloudflareTurnModel(url="")


def test_cloudflare_turn_model_uses_existing_worker_environment_names(monkeypatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://existing-worker.test")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "existing-token")
    monkeypatch.setenv("CLOUDFLARE_TIMEOUT", "12.5")

    model = CloudflareTurnModel()
    assert model.url == "https://existing-worker.test"
    assert model.token == "existing-token"
    assert model.timeout == 12.5


@pytest.mark.parametrize("json_object", (False, True))
def test_cloudflare_turn_model_converts_transport_failures_to_runtime_error(monkeypatch, json_object: bool) -> None:
    from urllib.error import URLError

    def urlopen(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    with pytest.raises(RuntimeError, match="Cloudflare AI agent request failed"):
        CloudflareTurnModel(url="https://agent.test").play_turn(
            RuntimeContext("v1", 1, {}), json_object=json_object
        )
