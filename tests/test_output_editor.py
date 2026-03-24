from __future__ import annotations

import json

import pytest

from storygame.llm.output_editor import OllamaOutputEditor, OpenAIOutputEditor, build_output_editor


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_build_output_editor_requires_llm_mode() -> None:
    assert isinstance(build_output_editor("openai"), OpenAIOutputEditor)
    assert isinstance(build_output_editor("ollama"), OllamaOutputEditor)
    with pytest.raises(ValueError, match="requires LLM mode"):
        build_output_editor("mock")


def test_openai_output_editor_passthrough_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    editor = OpenAIOutputEditor()
    lines = ["line 1", "line 2"]
    assert editor.review_opening(lines, "goal") == lines
    assert editor.review_turn(lines, "goal", turn_index=3, debug=False) == lines


def test_openai_output_editor_uses_llm_when_available(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    captured_requests: list[dict[str, object]] = []

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured_requests.append(json.loads(request.data.decode("utf-8")))
        return _FakeResponse('{"choices":[{"message":{"content":"{\\"lines\\":[\\"edited\\"]}"}}]}')

    monkeypatch.setattr("storygame.llm.output_editor.urllib.request.urlopen", _fake_urlopen)
    editor = OpenAIOutputEditor()
    assert editor.review_turn(["original"], "goal", turn_index=2, debug=False) == ["edited"]
    assert editor.review_opening(["opening"], "goal") == ["edited"]
    opening_instruction = json.loads(captured_requests[-1]["messages"][1]["content"])["instruction"]
    assert "prioritize character background, motivation, communication, and relationships" in opening_instruction.lower()


def test_ollama_output_editor_returns_input_on_invalid_payload(monkeypatch) -> None:
    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse('{"message":{"content":"not-json"}}')

    monkeypatch.setattr("storygame.llm.output_editor.urllib.request.urlopen", _fake_urlopen)
    editor = OllamaOutputEditor()
    lines = ["l1", "l2"]
    assert editor.review_opening(lines, "goal") == lines


def test_ollama_output_editor_uses_response_field_and_turn_debug_passthrough(monkeypatch) -> None:
    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse('{"response":"{\\"lines\\":[\\"edited-ollama\\"]}"}')

    monkeypatch.setattr("storygame.llm.output_editor.urllib.request.urlopen", _fake_urlopen)
    editor = OllamaOutputEditor()
    assert editor.review_turn(["orig"], "goal", turn_index=2, debug=False) == ["edited-ollama"]
    assert editor.review_turn(["keep"], "goal", turn_index=2, debug=True) == ["keep"]
