"""Bounded compilation of immutable causal-blueprint candidates."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from storygame.authoring.causal_contracts import (
    CausalCompiledStory,
    CausalValidationError,
    validate_causal_compiled_story,
)
from storygame.authoring.causal_critics import (
    CausalCompletenessCritic,
    CausalCriticResult,
    FreytagProgressionCritic,
    RouteFairnessCritic,
)
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from storygame.authoring.prompts import build_blueprint_compiler_prompt
from storygame.authoring.sources import NormalizedStorySource


class BlueprintCompilerTransport(Protocol):
    """Untrusted provider boundary with an explicit JSON-object selection."""

    def generate(self, prompt: str, *, json_object: bool) -> str | Mapping[str, object]: ...


class BlueprintCompilation(BaseModel):
    model_config = ConfigDict(frozen=True)

    story: CausalCompiledStory
    request_count: int
    validation_results: tuple[str, ...]
    accepted: bool = True
    diagnostics: tuple[CompilationDiagnostic, ...] = ()


class CompilationDiagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)

    critic: str
    code: str
    detail: str


def _parse_payload(response: str | Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(response, Mapping):
        return response
    try:
        payload = json.loads(response)
    except json.JSONDecodeError as exc:
        raise CompilationError("BLUEPRINT_OUTPUT_INVALID", "compiler response is not a JSON object") from exc
    if not isinstance(payload, Mapping):
        raise CompilationError("BLUEPRINT_OUTPUT_INVALID", "compiler response must be a JSON object")
    return payload


class BlueprintCompiler:
    """Compiles once, then spends at most one request on structured local repair."""

    def __init__(
        self,
        transport: BlueprintCompilerTransport,
        profiles: CausalProfileRegistry,
        *,
        provider: str,
        model: str,
        prompt_version: str = "story-blueprint-v2",
    ) -> None:
        self._transport = transport
        self._profiles = profiles
        self._provider = provider
        self._model = model
        self._prompt_version = prompt_version

    def compile(self, source: NormalizedStorySource) -> BlueprintCompilation:
        profile = self._profiles.resolve(source.profile)
        if profile.genre != source.genre:
            raise CompilationError("PROFILE_MISMATCH", "selected source genre does not match its profile")
        prompt = self._prompt(source, profile.model_dump(mode="json"))
        try:
            story = self._parse_and_validate(self._transport.generate(prompt, json_object=True), source)
        except CompilationError as exc:
            if exc.code != "OPENAI_JSON_MODE_REJECTED":
                return self._retry_unparseable(source, prompt)
            return self._retry_unparseable(source, prompt, json_object=False)
        diagnostics = self._critique(story)
        if not diagnostics:
            return self._accepted(story, 1)
        repair_prompt = self._prompt(source, profile.model_dump(mode="json"), diagnostics)
        try:
            repaired = self._parse_and_validate(self._transport.generate(repair_prompt, json_object=True), source)
        except CompilationError as exc:
            return self._rejected(story, 2, (*diagnostics, self._error_diagnostic(exc)))
        repaired_diagnostics = self._critique(repaired)
        if repaired_diagnostics:
            return self._rejected(repaired, 2, repaired_diagnostics)
        return self._accepted(repaired, 2, repaired=True)

    def _retry_unparseable(
        self,
        source: NormalizedStorySource,
        prompt: str,
        *,
        json_object: bool = False,
    ) -> BlueprintCompilation:
        try:
            story = self._parse_and_validate(self._transport.generate(prompt, json_object=json_object), source)
        except CompilationError as exc:
            raise CompilationError("BLUEPRINT_COMPILATION_EXHAUSTED", exc.detail) from exc
        diagnostics = self._critique(story)
        if diagnostics:
            return self._rejected(story, 2, diagnostics)
        return self._accepted(story, 2, repaired=True)

    def _parse_and_validate(
        self, response: str | Mapping[str, object], source: NormalizedStorySource
    ) -> CausalCompiledStory:
        try:
            story = validate_causal_compiled_story(_parse_payload(response))
        except CausalValidationError as exc:
            raise CompilationError(exc.code, exc.detail) from exc
        try:
            self._profiles.validate(story)
        except CausalValidationError as exc:
            raise CompilationError(exc.code, exc.detail) from exc
        self._validate_source(story, source)
        return story

    def _prompt(
        self,
        source: NormalizedStorySource,
        profile: Mapping[str, object],
        diagnostics: tuple[CompilationDiagnostic, ...] = (),
    ) -> str:
        return build_blueprint_compiler_prompt(
            source.premise,
            profile,
            source.provenance(),
            diagnostics=tuple(item.model_dump() for item in diagnostics),
        )

    def _critique(self, story: CausalCompiledStory) -> tuple[CompilationDiagnostic, ...]:
        results: tuple[CausalCriticResult, ...] = (
            CausalCompletenessCritic().critique(story),
            RouteFairnessCritic(self._profiles).critique(story),
            FreytagProgressionCritic(self._profiles).critique(story),
        )
        return tuple(
            CompilationDiagnostic(critic=result.critic, code="LOCAL_INVARIANT", detail=detail)
            for result in results
            for detail in result.diagnostics
        )

    def _accepted(
        self, story: CausalCompiledStory, request_count: int, *, repaired: bool = False
    ) -> BlueprintCompilation:
        results = ("local_contract_valid", "profile_valid", "source_verified", "critics_valid")
        if repaired:
            results += ("repair_valid",)
        return BlueprintCompilation(
            story=self._with_provenance(story, results),
            request_count=request_count,
            validation_results=results,
        )

    def _rejected(
        self,
        story: CausalCompiledStory,
        request_count: int,
        diagnostics: tuple[CompilationDiagnostic, ...],
    ) -> BlueprintCompilation:
        results = ("local_contract_valid", "profile_valid", "source_verified", "candidate_rejected")
        return BlueprintCompilation(
            story=self._with_provenance(story, results),
            request_count=request_count,
            validation_results=results,
            accepted=False,
            diagnostics=diagnostics,
        )

    def _with_provenance(self, story: CausalCompiledStory, results: tuple[str, ...]) -> CausalCompiledStory:
        provenance = story.provenance.model_copy(
            update={
                "provider": self._provider,
                "model": self._model,
                "response_id": getattr(self._transport, "last_request_id", None),
                "prompt_version": self._prompt_version,
                "validation_results": results,
            }
        )
        return story.model_copy(update={"provenance": provenance})

    @staticmethod
    def _error_diagnostic(error: CompilationError) -> CompilationDiagnostic:
        return CompilationDiagnostic(critic="repair", code=error.code, detail=error.detail)

    @staticmethod
    def _validate_source(story: CausalCompiledStory, source: NormalizedStorySource) -> None:
        if story.provenance.source_id != source.source_id or story.provenance.source_hash != source.source_hash:
            raise CompilationError(
                "SOURCE_PROVENANCE_MISMATCH", "candidate source identity or hash does not match selection"
            )
        if story.genre != source.genre or story.profile != source.profile:
            raise CompilationError("SOURCE_PROFILE_MISMATCH", "candidate genre or profile does not match selection")
