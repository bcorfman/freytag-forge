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
    """Owns the two-request recovery budget; transports never retry themselves."""

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
        prompt = build_blueprint_compiler_prompt(source.premise, profile.model_dump(mode="json"))
        errors: list[CompilationError] = []
        for request_count, json_object in enumerate((True, False), start=1):
            try:
                payload = _parse_payload(self._transport.generate(prompt, json_object=json_object))
                story = validate_causal_compiled_story(payload)
                self._profiles.validate(story)
                self._validate_source(story, source)
                provenance = story.provenance.model_copy(
                    update={
                        "source_path": source.source_path,
                        "source_schema_version": source.source_schema_version,
                        "provider": self._provider,
                        "model": self._model,
                        "response_id": getattr(self._transport, "last_request_id", None),
                        "prompt_version": self._prompt_version,
                        "validation_results": ("local_contract_valid", "profile_valid", "source_verified"),
                    }
                )
                return BlueprintCompilation(
                    story=story.model_copy(update={"provenance": provenance}),
                    request_count=request_count,
                    validation_results=provenance.validation_results,
                )
            except (CompilationError, CausalValidationError) as exc:
                errors.append(exc if isinstance(exc, CompilationError) else CompilationError(exc.code, exc.detail))
        raise CompilationError("BLUEPRINT_COMPILATION_EXHAUSTED", errors[-1].detail) from errors[-1]

    @staticmethod
    def _validate_source(story: CausalCompiledStory, source: NormalizedStorySource) -> None:
        if story.provenance.source_id != source.source_id or story.provenance.source_hash != source.source_hash:
            raise CompilationError(
                "SOURCE_PROVENANCE_MISMATCH", "candidate source identity or hash does not match selection"
            )
        if story.genre != source.genre or story.profile != source.profile:
            raise CompilationError("SOURCE_PROFILE_MISMATCH", "candidate genre or profile does not match selection")
