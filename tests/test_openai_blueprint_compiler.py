from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from storygame.authoring import openai_transport
from storygame.authoring.blueprint_compiler import BlueprintCompiler, BlueprintCompilerTransport, _parse_payload
from storygame.authoring.causal_contracts import validate_causal_compiled_story
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from storygame.authoring.openai_transport import OpenAIBlueprintTransport, OpenAICompilerConfig
from storygame.authoring.prompts import build_blueprint_compiler_prompt
from storygame.authoring.sources import NormalizedStorySource
from tests.test_causal_story_contract import _story


@dataclass
class FakeResponsesClient:
    responses: list[object]
    calls: list[dict[str, object]]

    def create_response(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _source() -> NormalizedStorySource:
    return NormalizedStorySource(
        source_format="story-outline-inventory-v1",
        source_id="signal",
        genre="sci-fi",
        profile="sci-fi",
        source_path="outlines.yaml#harbor_signal",
        source_schema_version="story-outline-inventory-v1",
        source_hash="a" * 64,
        premise="A beacon fails above an unstable sea.",
        opening_public_boundary="The beacon is failing.",
    )


def _candidate() -> dict[str, object]:
    return _story()


def _profiles() -> CausalProfileRegistry:
    return CausalProfileRegistry.from_directory(Path("data/genre_profiles"))


def test_openai_transport_requests_responses_json_object_and_normalizes_output():
    client = FakeResponsesClient([{"output_text": '{"ok": true}', "id": "resp_123"}], [])
    transport = OpenAIBlueprintTransport(
        OpenAICompilerConfig(api_key="sk-test-key", model="gpt-5.6", timeout_seconds=12), client
    )

    assert transport.generate("prompt", json_object=True) == {"ok": True}
    assert client.calls == [
        {
            "model": "gpt-5.6",
            "input": "prompt",
            "text": {"format": {"type": "json_object"}},
            "timeout_seconds": 12,
        }
    ]
    assert transport.last_request_id == "resp_123"


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"result": {"response": '{"ok": true}'}}, {"ok": True}),
        ({"choices": [{"message": {"content": '```json\n{"ok": true}\n```'}}]}, {"ok": True}),
        ({"output": [{"content": [{"type": "output_text", "text": '{"ok": true}'}]}]}, {"ok": True}),
    ],
)
def test_openai_transport_normalizes_supported_envelopes(response: object, expected: object):
    transport = OpenAIBlueprintTransport(
        OpenAICompilerConfig(api_key="sk-test-key", model="gpt-5.6"), FakeResponsesClient([response], [])
    )

    assert transport.generate("prompt", json_object=False) == expected


def test_openai_transport_surfaces_refusal_empty_json_mode_and_timeout_without_secrets():
    class JsonModeRejected(Exception):
        status_code = 400

    cases = [
        ({"refusal": "No."}, "OPENAI_REFUSAL"),
        ({"output_text": ""}, "OPENAI_EMPTY_OUTPUT"),
        (JsonModeRejected("response_format json_object unsupported"), "OPENAI_JSON_MODE_REJECTED"),
        (TimeoutError("timed out"), "OPENAI_TIMEOUT"),
    ]
    for response, code in cases:
        transport = OpenAIBlueprintTransport(
            OpenAICompilerConfig(api_key="sk-super-secret", model="gpt-5.6"), FakeResponsesClient([response], [])
        )
        with pytest.raises(CompilationError, match=code) as error:
            transport.generate("prompt", json_object=True)
        assert "sk-super-secret" not in str(error.value)


def test_openai_configuration_requires_key_and_explicit_model(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FREYTAG_COMPILER_MODEL", raising=False)
    with pytest.raises(CompilationError, match="OPENAI_API_KEY_REQUIRED"):
        OpenAICompilerConfig.from_environment()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    with pytest.raises(CompilationError, match="OPENAI_MODEL_REQUIRED"):
        OpenAICompilerConfig.from_environment()


def test_openai_default_responses_client_posts_to_the_configured_endpoint(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args: object):
            return False

        def read(self) -> bytes:
            return b'{"output_text":"{}"}'

    def fake_urlopen(request: object, *, timeout: float) -> Response:
        captured.update(
            {"url": request.full_url, "authorization": request.get_header("Authorization"), "timeout": timeout}
        )
        return Response()

    monkeypatch.setattr(openai_transport, "urlopen", fake_urlopen)
    transport = OpenAIBlueprintTransport(
        OpenAICompilerConfig(
            api_key="sk-test-key", model="gpt-5.6", base_url="https://example.test/v1/", timeout_seconds=8
        )
    )

    assert transport.generate("prompt", json_object=False) == {}
    assert captured == {
        "url": "https://example.test/v1/responses",
        "authorization": "Bearer sk-test-key",
        "timeout": 8.0,
    }


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (HTTPError("https://example.test", 500, "failure", {}, None), "OPENAI_TRANSPORT_ERROR"),
        (URLError("offline"), "OPENAI_TRANSPORT_ERROR"),
    ],
)
def test_openai_transport_sanitizes_network_errors(error: Exception, code: str):
    transport = OpenAIBlueprintTransport(
        OpenAICompilerConfig(api_key="sk-test-key", model="gpt-5.6"), FakeResponsesClient([error], [])
    )

    with pytest.raises(CompilationError, match=code):
        transport.generate("prompt", json_object=False)


def test_openai_transport_handles_raw_text_and_json_mode_http_rejection():
    transport = OpenAIBlueprintTransport(
        OpenAICompilerConfig(api_key="sk-test-key", model="gpt-5.6"),
        FakeResponsesClient(["not json", HTTPError("https://example.test", 400, "bad request", {}, None)], []),
    )

    assert transport.generate("prompt", json_object=False) == "not json"
    with pytest.raises(CompilationError, match="OPENAI_JSON_MODE_REJECTED"):
        transport.generate("prompt", json_object=True)


def test_blueprint_compiler_retries_once_without_json_mode_and_records_redacted_provenance():
    candidate = _candidate()
    candidate["provenance"] = _source().provenance()

    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.calls: list[bool] = []

        def generate(self, prompt: str, *, json_object: bool) -> str | dict[str, object]:
            self.calls.append(json_object)
            if json_object:
                raise CompilationError("OPENAI_JSON_MODE_REJECTED", "unsupported")
            return candidate

    transport = FakeTransport()
    compilation = BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.6").compile(_source())

    assert transport.calls == [True, False]
    assert compilation.request_count == 2
    assert compilation.story.provenance.provider == "openai"
    assert compilation.story.provenance.model == "gpt-5.6"
    assert "sk-" not in json.dumps(compilation.model_dump(mode="json"))


def test_blueprint_compiler_exhausts_after_two_malformed_attempts():
    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.calls: list[bool] = []

        def generate(self, prompt: str, *, json_object: bool) -> str:
            self.calls.append(json_object)
            return "not json"

    transport = FakeTransport()
    with pytest.raises(CompilationError, match="BLUEPRINT_COMPILATION_EXHAUSTED"):
        BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.6").compile(_source())
    assert transport.calls == [True, False]


def test_blueprint_compiler_repairs_structured_causal_diagnostics() -> None:
    incomplete = _candidate()
    incomplete["provenance"] = _source().provenance()
    incomplete["causal_events"][1]["output_truths"] = ["remedy"]
    repaired = _candidate()
    repaired["provenance"] = _source().provenance()

    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            assert json_object
            self.prompts.append(prompt)
            return incomplete if len(self.prompts) == 1 else repaired

    transport = FakeTransport()
    compilation = BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.6").compile(_source())

    assert compilation.accepted
    assert compilation.request_count == 2
    assert compilation.validation_results[-1] == "repair_valid"
    assert '"source_hash":"' + "a" * 64 in transport.prompts[0]
    assert "lacks a causal evidence/route chain" in transport.prompts[1]
    assert "Diagnostics:" in transport.prompts[1]


def test_blueprint_compiler_persists_unplayable_candidate_diagnostics() -> None:
    incomplete = _candidate()
    incomplete["provenance"] = _source().provenance()
    incomplete["causal_events"][1]["output_truths"] = ["remedy"]

    class FakeTransport(BlueprintCompilerTransport):
        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            return incomplete

    compilation = BlueprintCompiler(FakeTransport(), _profiles(), provider="openai", model="gpt-5.6").compile(_source())

    assert not compilation.accepted
    assert compilation.story.provenance.validation_results[-1] == "candidate_rejected"
    assert compilation.diagnostics[0].critic == "causal_completeness"


def test_blueprint_prompt_requires_backwards_planning_without_genre_branches() -> None:
    prompt = build_blueprint_compiler_prompt(
        "A crew must solve a crisis.",
        {"genre": "sci-fi", "minimum_independent_proof_routes": 2},
        _source().provenance(),
    )

    assert "terminal truths; enumerate causal events and timeline; work backward" in prompt
    assert "independently realizable proof routes" in prompt
    assert "source_hash" in prompt
    assert "mystery" not in prompt


def test_blueprint_parser_and_source_validation_reject_untrusted_shapes():
    assert _parse_payload("{}") == {}
    with pytest.raises(CompilationError, match="BLUEPRINT_OUTPUT_INVALID"):
        _parse_payload("[]")

    class FakeTransport(BlueprintCompilerTransport):
        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            candidate = _candidate()
            candidate["provenance"] = {
                "source_format": "story-outline-inventory-v1",
                "source_id": "wrong",
                "source_hash": "a" * 64,
            }
            return candidate

    with pytest.raises(CompilationError, match="BLUEPRINT_COMPILATION_EXHAUSTED"):
        BlueprintCompiler(FakeTransport(), _profiles(), provider="openai", model="gpt-5.6").compile(_source())


def test_blueprint_compiler_rejects_profile_mismatches_before_and_after_generation():
    class NeverCalled(BlueprintCompilerTransport):
        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            raise AssertionError("profile mismatch must fail before inference")

    compiler = BlueprintCompiler(NeverCalled(), _profiles(), provider="openai", model="gpt-5.6")
    with pytest.raises(CompilationError, match="PROFILE_MISMATCH"):
        compiler.compile(_source().model_copy(update={"genre": "fantasy"}))

    candidate = _candidate()
    candidate["provenance"] = _source().provenance()
    story = validate_causal_compiled_story(candidate)
    with pytest.raises(CompilationError, match="SOURCE_PROFILE_MISMATCH"):
        compiler._validate_source(story, _source().model_copy(update={"profile": "fantasy"}))
