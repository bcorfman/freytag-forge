from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from storygame.authoring.blueprint_compiler import (
    BlueprintCompilationError,
    BlueprintCompiler,
    RouteFairnessCritic,
)
from storygame.authoring.genre_profiles import GenreProfileRegistry


def _payload(outline: str = "outline", outline_id: str = "vale_outline") -> dict[str, object]:
    payload = json.loads(Path("data/story_blueprints/v1/mystery.json").read_text(encoding="utf-8"))
    payload["source_outline"] = {"id": outline_id, "content_hash": hashlib.sha256(outline.encode()).hexdigest()}
    return payload


class _Transport:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.json_modes: list[bool] = []

    def generate(self, prompt: str, *, json_object: bool) -> object:
        assert "STORY_BLUEPRINT_JSON" in prompt
        self.json_modes.append(json_object)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _compiler(transport: _Transport, **kwargs: object) -> BlueprintCompiler:
    return BlueprintCompiler(transport, GenreProfileRegistry.from_directory(), **kwargs)


def test_blueprint_compiler_uses_json_object_mode_and_records_reviewable_provenance():
    outline = "A detective must establish what happened before the storm destroys the evidence."
    payload = _payload(outline)
    result = _compiler(_Transport([json.dumps(payload)])).compile(
        outline,
        genre="mystery",
        source_outline_id="vale_outline",
        model_metadata={"model": "test-large"},
    )

    assert result.blueprint.id == "mystery_minimal"
    assert result.provenance.source_outline_hash == hashlib.sha256(outline.encode()).hexdigest()
    assert result.provenance.prompt_version == "story-blueprint-compiler-v1"
    assert result.provenance.model_metadata == {"model": "test-large"}
    assert result.provenance.critic_results[-1].critic == "route_fairness"


def test_blueprint_compiler_retries_once_without_json_mode_and_rejects_invalid_candidate():
    compiler = _compiler(_Transport([RuntimeError("json mode unsupported"), "not json"]))

    with pytest.raises(BlueprintCompilationError, match="BLUEPRINT_COMPILATION_EXHAUSTED"):
        compiler.compile("outline", genre="mystery", source_outline_id="vale_outline")

    assert compiler.request_count == 2


def test_route_fairness_rejects_one_path_for_required_revelation_when_profile_requires_two():
    critic = RouteFairnessCritic(GenreProfileRegistry.from_directory())
    report = critic.critique(
        _compiler(_Transport([_payload()]))
        .compile("outline", genre="mystery", source_outline_id="vale_outline", critics=())
        .blueprint,
        {},
    )

    assert report.accepted is False
    assert "identify_perpetrator" in report.diagnostics[0]


def test_blueprint_compiler_permits_one_repair_and_revalidates_it():
    payload = _payload()
    for route in list(payload["realization_routes"]):
        alternate = dict(route)
        alternate["id"] = f"{route['id']}_alternate"
        alternate["role"] = "testimony"
        payload["realization_routes"].append(alternate)

    class RejectingCritic:
        calls = 0

        def critique(self, blueprint, opening_facts):
            from storygame.authoring.blueprint_compiler import BlueprintCriticResult

            self.calls += 1
            return BlueprintCriticResult("continuity", self.calls > 1, ("repair the title",))

    class Repairer:
        def repair(self, blueprint, diagnostics):
            changed = blueprint.model_dump(mode="json")
            changed["title"] = "Reviewed Vale Mansion"
            return changed

    result = _compiler(_Transport([payload]), critics=(RejectingCritic(),), repairer=Repairer()).compile(
        "outline", genre="mystery", source_outline_id="vale_outline"
    )

    assert result.accepted is True
    assert result.blueprint.title == "Reviewed Vale Mansion"
    assert result.provenance.repair_applied is True


def test_live_blueprint_compilation_requires_explicit_opt_in(monkeypatch):
    compiler = _compiler(_Transport([_payload()]))

    with pytest.raises(BlueprintCompilationError, match="LIVE_COMPILATION_DISABLED"):
        compiler.compile_live("outline", genre="mystery", source_outline_id="vale_outline")

    monkeypatch.setenv("FREYTAG_ENABLE_LIVE_COMPILER", "1")
    assert compiler.compile_live("outline", genre="mystery", source_outline_id="vale_outline").accepted is False
