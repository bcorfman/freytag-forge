from __future__ import annotations

import json
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from storygame.authoring import openai_transport
from storygame.authoring.blueprint_compiler import (
    BlueprintCompilationExhausted,
    BlueprintCompiler,
    BlueprintCompilerTransport,
    _apply_source_opening_suggestions,
    _parse_payload,
)
from storygame.authoring.causal_contracts import validate_causal_compiled_story
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from storygame.authoring.openai_transport import OpenAIBlueprintTransport, OpenAICompilerConfig
from storygame.authoring.prompts import build_blueprint_compiler_prompt
from storygame.authoring.sources import NormalizedStorySource
from tests.test_causal_spatial_projection_phase3 import _phase3_story


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
    return _phase3_story()


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
            "reasoning": {"effort": "high"},
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


def test_compiler_projects_explicit_source_opening_targets() -> None:
    source = _source().model_copy(
        update={
            "opening_setup": {
                "first_available_actions": ("Question the guide.",),
                "first_action_suggestions": (
                    {"text": "Question the guide.", "target_kind": "participant", "target_id": "guide"},
                ),
            }
        }
    )
    payload = {"opening": {"first_available_actions": ["Inspect the sea."], "first_action_suggestions": []}}

    projected = _apply_source_opening_suggestions(payload, source)

    assert projected["opening"] == {
        "first_available_actions": ("Question the guide.",),
        "first_action_suggestions": (
            {"text": "Question the guide.", "target_kind": "participant", "target_id": "guide"},
        ),
    }


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


def test_openai_configuration_requires_key_and_resolves_the_selected_quality_tier(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(CompilationError, match="OPENAI_API_KEY_REQUIRED"):
        OpenAICompilerConfig.from_environment(quality_tier="preferred")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    preferred = OpenAICompilerConfig.from_environment(quality_tier="preferred")
    minimum = OpenAICompilerConfig.from_environment(quality_tier="minimum")

    assert (preferred.model, preferred.reasoning_effort) == ("gpt-5.6-sol", "high")
    assert (minimum.model, minimum.reasoning_effort) == ("gpt-5.6-terra", "high")
    debug = OpenAICompilerConfig.from_environment(debug=True)
    assert (debug.model, debug.reasoning_effort) == ("gpt-5.6-luna", "low")
    with pytest.raises(CompilationError, match="COMPILER_QUALITY_TIER_INVALID"):
        OpenAICompilerConfig.from_environment(quality_tier="luna")


def test_openai_configuration_accepts_an_explicit_finite_timeout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    config = OpenAICompilerConfig.from_environment(quality_tier="minimum", timeout_seconds=120)

    assert config.timeout_seconds == 120


def test_openai_configuration_defaults_to_background_polling_with_a_ten_minute_deadline(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    config = OpenAICompilerConfig.from_environment(quality_tier="minimum")

    assert config.timeout_seconds == 600
    assert config.background is True


def test_openai_configuration_rejects_a_nonpositive_timeout_from_the_cli():
    with pytest.raises(CompilationError, match="OPENAI_TIMEOUT_INVALID"):
        OpenAICompilerConfig(api_key="sk-test-key", model="gpt-5.5", timeout_seconds=0)


def test_openai_transport_polls_a_background_response_to_completion(monkeypatch: pytest.MonkeyPatch):
    class BackgroundClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []
            self.retrievals: list[tuple[str, float]] = []

        def create_response(self, **kwargs: object) -> object:
            self.calls.append(kwargs)
            return {"id": "resp_123", "status": "queued"}

        def retrieve_response(self, response_id: str, *, timeout_seconds: float) -> object:
            self.retrievals.append((response_id, timeout_seconds))
            return {"id": response_id, "status": "completed", "output_text": '{"ok": true}'}

    monkeypatch.setattr(openai_transport.time, "sleep", lambda _: None)
    client = BackgroundClient()
    transport = OpenAIBlueprintTransport(
        OpenAICompilerConfig(api_key="sk-test-key", model="gpt-5.5", timeout_seconds=120, background=True), client
    )

    assert transport.generate("prompt", json_object=True) == {"ok": True}
    assert client.calls[0]["background"] is True
    assert client.retrievals[0][0] == "resp_123"


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


def test_openai_transport_surfaces_only_safe_rate_and_project_limit_metadata():
    headers = Message()
    headers["x-request-id"] = "req_123"
    headers["x-ratelimit-remaining-requests"] = "0"
    headers["x-ratelimit-reset-requests"] = "1m"
    headers["x-ratelimit-remaining-project-tokens"] = "0"
    headers["x-ratelimit-reset-project-tokens"] = "24h"
    headers["authorization"] = "Bearer should-not-appear"
    error = HTTPError("https://example.test", 429, "limit", headers, None)
    transport = OpenAIBlueprintTransport(
        OpenAICompilerConfig(api_key="sk-super-secret", model="gpt-5.6"), FakeResponsesClient([error], [])
    )

    with pytest.raises(CompilationError, match="OPENAI_RATE_LIMIT") as raised:
        transport.generate("prompt", json_object=False)

    detail = str(raised.value)
    assert "request_id=req_123" in detail
    assert "remaining_requests=0" in detail
    assert "reset_requests=1m" in detail
    assert "remaining_project_tokens=0" in detail
    assert "reset_project_tokens=24h" in detail
    assert "should-not-appear" not in detail
    assert "sk-super-secret" not in detail


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
    assert transport.calls == [True, True]


def test_blueprint_compiler_retains_nonplayable_attempts_for_explicit_diagnostics():
    class FakeTransport(BlueprintCompilerTransport):
        def generate(self, prompt: str, *, json_object: bool) -> str:
            return "not json"

    compiler = BlueprintCompiler(FakeTransport(), _profiles(), provider="openai", model="gpt-5.5")
    with pytest.raises(BlueprintCompilationExhausted) as raised:
        compiler.compile(_source())

    artifact = raised.value.diagnostic_artifact()
    assert artifact["schema_version"] == "story-blueprint-diagnostic-v1"
    assert artifact["source"]["source_id"] == "signal"
    assert [attempt["json_object"] for attempt in artifact["attempts"]] == [True, True]
    assert [attempt["response"] for attempt in artifact["attempts"]] == ["not json", "not json"]
    assert all(attempt["error_code"] == "BLUEPRINT_OUTPUT_INVALID" for attempt in artifact["attempts"])


def test_blueprint_compiler_retries_invalid_contracts_with_the_local_diagnostic():
    candidate = _candidate()
    candidate["provenance"] = _source().provenance()
    invalid = _candidate()
    invalid["provenance"] = _source().provenance()
    del invalid["truths"][0]["summary"]
    invalid["locations"][0]["initial_access"] = "not_a_boolean"
    invalid["causal_events"][1]["earliest"] = -1
    for beat in invalid["required_beats"]:
        beat["pressure"] = "escalating"
    for beat in invalid["optional_beats"]:
        beat["pressure"] = "side_story"
        beat["purpose"] = "optional"

    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.prompts: list[str] = []
            self.calls: list[bool] = []

        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            self.prompts.append(prompt)
            self.calls.append(json_object)
            return invalid if len(self.prompts) == 1 else candidate

    transport = FakeTransport()
    compilation = BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.5").compile(_source())

    assert compilation.accepted
    assert "truths.0.summary: missing" in transport.prompts[1]
    assert "locations.0.initial_access: bool_parsing" in transport.prompts[1]
    assert "causal_events.1.earliest: greater_than_equal" in transport.prompts[1]
    assert "required_beats.0.pressure: int_parsing" in transport.prompts[1]
    assert "optional_beats.0.purpose: literal_error" in transport.prompts[1]
    assert "Candidate JSON to correct" in transport.prompts[1]
    assert '"schema_version":"story-blueprint-v2"' in transport.prompts[1]
    assert transport.calls == [True, True]


def test_blueprint_compiler_repair_names_interaction_cross_field_failure() -> None:
    invalid = _candidate()
    invalid["provenance"] = _source().provenance()
    invalid["interaction_frames"][0]["location_ids"] = ["dock"]
    candidate = _candidate()
    candidate["provenance"] = _source().provenance()

    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            self.prompts.append(prompt)
            return invalid if len(self.prompts) == 1 else candidate

    transport = FakeTransport()

    compilation = BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.6").compile(_source())

    assert compilation.accepted
    assert "INTERACTION_LOCATION_INCOMPATIBLE: engineer_warning" in transport.prompts[1]
    assert "interaction_frames[].location_ids must be a subset" in transport.prompts[1]
    assert "destination_location_id must appear in that frame's location_ids" in transport.prompts[1]


def test_blueprint_compiler_repair_explains_interaction_marker_and_exit_rules() -> None:
    invalid = _candidate()
    invalid["provenance"] = _source().provenance()
    invalid["interaction_frames"][0]["abort_truth_ids"] = ["tradeoff"]
    invalid["storylets"][1]["abort_truth_ids"] = ["tradeoff"]
    candidate = _candidate()
    candidate["provenance"] = _source().provenance()

    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            self.prompts.append(prompt)
            return invalid if len(self.prompts) == 1 else candidate

    transport = FakeTransport()

    assert BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.6").compile(_source()).accepted
    assert "INTERACTION_MARKER_INVALID" in transport.prompts[1]
    assert "must be pairwise distinct" in transport.prompts[1]
    assert "npc_initiated or either must declare at least one abort_truth_id" in transport.prompts[1]


def test_blueprint_compiler_repair_requires_end_state_outcome_truths() -> None:
    invalid = _candidate()
    invalid["provenance"] = _source().provenance()
    invalid["end_states"][0]["required_truth_ids"] = ["remedy"]
    candidate = _candidate()
    candidate["provenance"] = _source().provenance()

    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            self.prompts.append(prompt)
            return invalid if len(self.prompts) == 1 else candidate

    transport = FakeTransport()

    assert BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.6").compile(_source()).accepted
    assert "ENDING_TRUTH_MISMATCH" in transport.prompts[1]
    assert "every outcome's truth_id must also appear" in transport.prompts[1]


def test_blueprint_compiler_reports_latent_errors_behind_invalid_source_metadata():
    invalid = _candidate()
    invalid["provenance"] = _source().provenance()
    invalid["profile"] = {"genre": "sci-fi"}
    invalid["timeline_constraints"] = [{"before_event_id": "repair_event", "after_event_id": "failure_event"}]
    candidate = _candidate()
    candidate["provenance"] = _source().provenance()

    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            self.prompts.append(prompt)
            return invalid if len(self.prompts) == 1 else candidate

    transport = FakeTransport()
    assert BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.5").compile(_source()).accepted
    assert "profile: string_type" in transport.prompts[1]
    assert "source-normalized preflight: TIMELINE_INVALID" in transport.prompts[1]


def test_blueprint_compiler_repairs_authoring_metadata_leaks_from_fictional_fields():
    invalid = _candidate()
    invalid["provenance"] = _source().provenance()
    invalid["truths"][0]["summary"] = "A reviewed causal artifact proves the system failure."
    candidate = _candidate()
    candidate["provenance"] = _source().provenance()

    class FakeTransport(BlueprintCompilerTransport):
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
            self.prompts.append(prompt)
            return invalid if len(self.prompts) == 1 else candidate

    transport = FakeTransport()
    compilation = BlueprintCompiler(transport, _profiles(), provider="openai", model="gpt-5.6").compile(_source())

    assert compilation.accepted
    assert "fictional fields reference authoring metadata" in transport.prompts[1]
    assert "reviewed causal artifact" in transport.prompts[1]


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
    assert "Candidate JSON to correct" in transport.prompts[1]
    assert "all three links" in transport.prompts[1]
    assert "at least the profile minimum of distinct opportunity kinds" in transport.prompts[1]
    assert "add a matching route rather than" in transport.prompts[1]
    assert "Never use a later beat as the gate" in transport.prompts[1]
    assert '"id":"signal_crisis"' in transport.prompts[1]


def test_blueprint_compiler_repair_prompt_requires_unknown_truth_references_to_match_declared_ids() -> None:
    candidate = _candidate()
    candidate["provenance"] = _source().provenance()
    candidate["realization_routes"][0]["failure_forward"]["consequence_truth_ids"] = ["missing_truth"]

    prompt = BlueprintCompiler._candidate_repair_prompt(
        "Diagnostics: route 'diagnose_scan' failure-forward references unknown 'missing_truth'",
        candidate,
    )

    assert "UNKNOWN_REFERENCE repair protocol" in prompt
    assert "declared truths[].id values" in prompt
    assert "CUSTODY_INCOMPATIBLE repair protocol" in prompt
    assert "preserve the separate alternative-suspect routes" in prompt
    assert "party_knowledge[].truth_ids specifically" in prompt
    assert "unknown connected-route prerequisite" in prompt
    assert "TIMELINE_INVALID repair protocol" in prompt
    assert "preserve causal event prerequisite ordering" in prompt
    assert "FAILURE_FORWARD_DEAD_END repair protocol" in prompt
    assert "one of that route's own result_truth_ids" in prompt
    assert "alternative_route_ids" in prompt
    assert "Preserve every existing reference list and its order" in prompt
    assert "CAUSAL_COMPLETENESS repair protocol" in prompt
    assert "ROUTE_FAIRNESS repair protocol" in prompt
    assert "END_STATE repair protocol" in prompt
    assert "must list every declared required_outcomes[].id, not merely one outcome" in prompt
    assert "STORYLET_ENUM repair protocol" in prompt
    assert "STORYLET_BEAT_NAMESPACE repair protocol" in prompt
    assert "STORYLET_MARKER repair protocol" in prompt
    assert "DRAMATIC_ESCALATION repair protocol" in prompt
    assert "PARTICIPANT_CONTINUITY repair protocol" in prompt
    assert "activation_truth_id must also appear" in prompt
    assert "social_complication, relationship, conflict, moral_choice, transition, or reversal" in prompt
    assert "For rejected pressure fields, use minimum and maximum, never min or max" in prompt
    assert "Reference inventory for repair follows" in prompt
    assert "Prior valid symbol ledger" in prompt
    assert "UNRELATED_REPAIR_CHANGE" not in prompt
    assert '"evidence_opportunity_truth_ids":{"crew_testimony":"tradeoff"' in prompt
    assert (
        '"truth_ids":["constraint","failure","interaction_aborted","interaction_continuing",'
        '"interaction_recent","opening","remedy","tradeoff"]' in prompt
    )
    assert "missing_truth" in prompt


def test_blueprint_compiler_marks_reference_inventory_unavailable_for_malformed_candidates() -> None:
    prompt = BlueprintCompiler._candidate_repair_prompt("Diagnostics: malformed output", "{")

    assert "Reference inventory: unavailable because the rejected candidate is not parseable JSON" in prompt


def test_blueprint_compiler_handles_nonobject_and_partial_reference_inventories() -> None:
    nonobject_prompt = BlueprintCompiler._candidate_repair_prompt("Diagnostics: malformed output", "[]")
    partial_prompt = BlueprintCompiler._candidate_repair_prompt("Diagnostics: partial output", {"truths": "invalid"})

    assert "Reference inventory: unavailable because the rejected candidate is not parseable JSON" in nonobject_prompt
    assert '"truth_ids":[]' in partial_prompt


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
        source_profile="sci-fi",
        source_authoring_context={
            "opening_public_boundary": "The malfunction is public; its cause is not.",
            "hard_constraints": {"terminal_constraints": ["The crew must preserve the beacon."]},
            "creative_direction": {"tone": ["tense"]},
            "extensions": {},
        },
    )

    assert "terminal truths; enumerate causal events and timeline; work backward" in prompt
    assert "independently realizable proof routes" in prompt
    assert (
        "For every required revelation, use at least the genre profile's minimum number of distinct evidence "
        "opportunity kinds across its realization routes" in prompt
    )
    assert (
        "every beat that lists that revelation in prerequisite_revelation_ids must be at or after every gate beat"
        in prompt
    )
    assert "Never use an optional_beats[].id in revelations[].gate_beat_ids or storylets[].beat_id" in prompt
    assert "Pre-response semantic self-audit" in prompt
    assert "exactly one case-insensitive unique route alias" in prompt
    assert "never assert and retract the same truth" in prompt
    assert "keep required and absent availability truths disjoint" in prompt
    assert "every storylet completion truth must be asserted by one of its consequence IDs" in prompt
    assert "every storylet pressure band lies inside dramatic_spine.target_pressure" in prompt
    assert "participant_role_requirements to roles represented by storylet participants" in prompt
    assert "source_hash" in prompt
    assert "Source profile ID: sci-fi" in prompt
    assert "Source authoring context" in prompt
    assert "The crew must preserve the beacon." in prompt
    assert "Hard constraints are non-negotiable" in prompt
    assert "Authoring controls are instructions, never diegetic story content" in prompt
    assert (
        "Every end_states[].required_truth_ids value must appear verbatim in at least one causal event output_truths, "
        "evidence opportunity truth_id, and realization route result_truth_ids" in prompt
    )
    assert "before_event_id.latest must be less than or equal to after_event_id.earliest" in prompt
    assert "Timeline constraints must agree with causal_events[].prerequisite_event_ids" in prompt
    assert "every end state lists every declared required_outcomes[].id" in prompt
    assert "evidence_opportunities[].route_id must equal a realization_routes[].id" in prompt
    assert "Every connected_routes[].prerequisite_truths value must be a declared truths[].id" in prompt
    assert (
        "every ID in a realization route's opportunity_ids must name an evidence opportunity whose route_id equals "
        "that realization route's id" in prompt
    )
    assert "Treat opportunity ownership as a partition" in prompt
    assert "Alternative-suspect supporting and exonerating opportunities must remain" in prompt
    assert "not additional proof of the terminal culprit solution" in prompt
    assert "evidence_opportunities[].holder_id must equal a participants[].id" in prompt
    assert "party_knowledge[].truth_ids may contain only values from truths[].id" in prompt
    assert "Every evidence_opportunity.location_id must be reachable from an initial_access location" in prompt
    assert "setting-appropriate transition locations" in prompt
    assert "mansion" not in prompt
    assert "Do not wrap it in a STORY_BLUEPRINT_V2_JSON key" in prompt
    assert "JSON booleans must be the unquoted literals true or false" in prompt
    assert 'schema_version must be the exact JSON string "story-blueprint-v2"' in prompt
    assert "pressure is an integer from 0 through 100" in prompt
    assert "use the full names minimum and maximum, never min or max" in prompt
    assert "direct_action, investigation, negotiation, dialogue, observation, travel, or conflict" in prompt
    assert "Do not use synonyms such as confrontation, discovery, interrogation, persuasion, or social" in prompt
    assert "investigation, social_complication, relationship, conflict, moral_choice, transition, or reversal" in prompt
    assert (
        "Do not use generic alternatives such as discovery, interrogation, persuasion, social, exploration, "
        "or complication" in prompt
    )
    assert "alternative_satisfier, complication, relationship_development, or world_development" in prompt
    assert "is mandatory on every optional beat whose purpose is alternative_satisfier" in prompt
    assert "A plausible alternative suspect is not automatically an alternative_satisfier" in prompt
    assert "profile must be the exact Source profile ID JSON string, never an object" in prompt
    assert 'initial_availability must be exactly one of "present", "away", or "unavailable"' in prompt
    assert "initial_access must be the JSON boolean true or false" in prompt
    assert 'kind must be exactly one of "scene_evidence", "document", "testimony", or "item"' in prompt
    assert 'initiation must be exactly one of "npc_initiated", "player_initiated", or "either"' in prompt
    assert "agency_modes items may only be engage, refuse, redirect, interrupt, or depart" in prompt
    assert "priority must be an integer from 0 through 100" in prompt
    assert "first_action_suggestions" in prompt
    assert "interaction_frames[].location_ids must be a subset" in prompt
    assert "destination_location_id must appear in that frame's location_ids" in prompt
    assert "activation, continuation, completion, recent-use, and abort truth IDs must be pairwise distinct" in prompt
    assert "npc_initiated or either must declare at least one abort_truth_id" in prompt
    assert "Every failure_forward.consequence_truth_ids array must contain at least one declared truth ID" in prompt
    assert (
        "A required outcome may be assigned to an alternative_satisfier optional beat only when at least one "
        "required beat also names that outcome" in prompt
    )
    assert 'truths: [{"id":"lowercase_id","summary":"non-empty summary","roles":["profile_role"]?}]' in prompt
    assert "realization_routes: [{id,revelation_id,opportunity_ids,result_truth_ids,failure_forward}]" in prompt
    assert "suspect_hypotheses: [{participant_id,supporting_truth_ids,exonerating_truth_ids}]" in prompt
    assert "When the genre profile requires alternative suspects" in prompt
    assert (
        "Every route's failure_forward must either establish at least one of that route's result_truth_ids or name "
        "an alternative realization route" in prompt
    )
    assert "mystery" not in prompt
    assert "dramatic_spine, consequences, storylets" in prompt
    assert (
        "Plan causal truths, locations, revelations, and endings before the dramatic spine and storylet pool" in prompt
    )
    assert "storylets: [{id,beat_id,purpose,route_family,availability,priority,dramatic_question" in prompt


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
