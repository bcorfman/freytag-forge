"""Offline, opt-in compilation and review for immutable Story Blueprints."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from storygame.authoring.blueprint_contracts import BlueprintValidationError, StoryBlueprint, validate_story_blueprint
from storygame.authoring.genre_profiles import GenreProfileRegistry
from storygame.authoring.prompts import build_blueprint_compiler_prompt

PROMPT_VERSION = "story-blueprint-compiler-v1"


class BlueprintCompilationError(ValueError):
    """A bounded offline compilation failure; candidates are never playable."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class BlueprintCompilerTransport(Protocol):
    """Provider adapter that explicitly receives the JSON-object transport choice."""

    def generate(self, prompt: str, *, json_object: bool) -> str | Mapping[str, object]: ...


class BlueprintCritic(Protocol):
    def critique(self, blueprint: StoryBlueprint, opening_facts: Mapping[str, object]) -> BlueprintCriticResult: ...


class BlueprintRepairer(Protocol):
    def repair(self, blueprint: StoryBlueprint, diagnostics: tuple[str, ...]) -> Mapping[str, object] | str: ...


@dataclass(frozen=True)
class BlueprintCriticResult:
    critic: str
    accepted: bool
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlueprintProvenance:
    prompt_version: str
    source_outline_hash: str
    source_outline_id: str
    model_metadata: Mapping[str, str]
    validation_diagnostics: tuple[str, ...]
    critic_results: tuple[BlueprintCriticResult, ...]
    request_count: int
    repair_applied: bool


@dataclass(frozen=True)
class BlueprintCompilation:
    blueprint: StoryBlueprint
    accepted: bool
    provenance: BlueprintProvenance


def _parse_payload(response: str | Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(response, Mapping):
        return response
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BlueprintCompilationError("BLUEPRINT_OUTPUT_INVALID", "compiler response is not a JSON object") from exc
    if not isinstance(payload, Mapping):
        raise BlueprintCompilationError("BLUEPRINT_OUTPUT_INVALID", "compiler response must be a JSON object")
    return payload


class RouteFairnessCritic:
    """Checks distinct player-facing paths without embedding any genre name."""

    def __init__(self, profiles: GenreProfileRegistry) -> None:
        self._profiles = profiles

    def critique(self, blueprint: StoryBlueprint, opening_facts: Mapping[str, object]) -> BlueprintCriticResult:
        profile = self._profiles.profile(blueprint.genre)
        minimum = profile.minimum_routes_per_required_revelation
        by_revelation: dict[str, set[str]] = {}
        for route in blueprint.realization_routes:
            by_revelation.setdefault(route.revelation_id, set()).add(route.role)
        diagnostics = tuple(
            f"required revelation '{revelation.id}' has fewer than {minimum} distinct route roles"
            for revelation in blueprint.revelations
            if revelation.required and len(by_revelation.get(revelation.id, set())) < minimum
        )
        return BlueprintCriticResult("route_fairness", not diagnostics, diagnostics)


class BlueprintCompiler:
    """Compiles one raw outline offline, then locally validates and reviews it."""

    def __init__(
        self,
        transport: BlueprintCompilerTransport | None,
        profiles: GenreProfileRegistry,
        *,
        critics: Sequence[BlueprintCritic] = (),
        repairer: BlueprintRepairer | None = None,
    ) -> None:
        self._transport = transport
        self._profiles = profiles
        self._critics = tuple(critics)
        self._repairer = repairer
        self.request_count = 0

    def compile(
        self,
        outline: str,
        *,
        genre: str,
        source_outline_id: str,
        opening_facts: Mapping[str, object] | None = None,
        model_metadata: Mapping[str, str] | None = None,
        critics: Sequence[BlueprintCritic] | None = None,
    ) -> BlueprintCompilation:
        if self._transport is None:
            raise BlueprintCompilationError(
                "COMPILER_TRANSPORT_UNAVAILABLE", "an injected compiler transport is required"
            )
        self.request_count = 0
        profile = self._profiles.profile(genre)
        prompt = build_blueprint_compiler_prompt(outline, profile.model_dump(mode="json"))
        blueprint, diagnostics = self._generate_validated(prompt, genre, source_outline_id, outline)
        selected_critics = tuple(critics) if critics is not None else self._critics
        reports = self._review(blueprint, opening_facts or {}, (*selected_critics, RouteFairnessCritic(self._profiles)))
        repaired = False
        if not all(report.accepted for report in reports) and self._repairer is not None:
            feedback = tuple(item for report in reports for item in report.diagnostics)
            blueprint = self._validate_candidate(
                _parse_payload(self._repairer.repair(blueprint, feedback)), genre, source_outline_id, outline
            )
            reports = self._review(
                blueprint, opening_facts or {}, (*selected_critics, RouteFairnessCritic(self._profiles))
            )
            repaired = True
        provenance = BlueprintProvenance(
            prompt_version=PROMPT_VERSION,
            source_outline_hash=hashlib.sha256(outline.encode("utf-8")).hexdigest(),
            source_outline_id=source_outline_id,
            model_metadata=dict(model_metadata or {}),
            validation_diagnostics=diagnostics,
            critic_results=reports,
            request_count=self.request_count,
            repair_applied=repaired,
        )
        return BlueprintCompilation(blueprint, all(report.accepted for report in reports), provenance)

    def compile_live(self, outline: str, **kwargs: object) -> BlueprintCompilation:
        if os.getenv("FREYTAG_ENABLE_LIVE_COMPILER") != "1":
            raise BlueprintCompilationError(
                "LIVE_COMPILATION_DISABLED", "set FREYTAG_ENABLE_LIVE_COMPILER=1 to use a model"
            )
        return self.compile(outline, **kwargs)  # type: ignore[arg-type]

    def _generate_validated(
        self, prompt: str, genre: str, source_outline_id: str, outline: str
    ) -> tuple[StoryBlueprint, tuple[str, ...]]:
        errors: list[str] = []
        for json_object in (True, False):
            try:
                self.request_count += 1
                payload = _parse_payload(self._transport.generate(prompt, json_object=json_object))  # type: ignore[union-attr]
                return self._validate_candidate(payload, genre, source_outline_id, outline), tuple(errors)
            except (BlueprintCompilationError, BlueprintValidationError, RuntimeError) as exc:
                errors.append(str(exc))
        raise BlueprintCompilationError("BLUEPRINT_COMPILATION_EXHAUSTED", "; ".join(errors))

    def _validate_candidate(
        self, payload: Mapping[str, object], genre: str, source_outline_id: str, outline: str
    ) -> StoryBlueprint:
        try:
            blueprint = validate_story_blueprint(payload)
            if blueprint.genre != genre:
                raise BlueprintValidationError("GENRE_PROFILE_MISMATCH", f"expected '{genre}'")
            expected_hash = hashlib.sha256(outline.encode("utf-8")).hexdigest()
            if (
                blueprint.source_outline.id != source_outline_id
                or blueprint.source_outline.content_hash != expected_hash
            ):
                raise BlueprintValidationError(
                    "SOURCE_OUTLINE_MISMATCH", "candidate provenance does not match the selected outline"
                )
            return self._profiles.validate(blueprint)
        except BlueprintValidationError as exc:
            raise BlueprintCompilationError(exc.code, exc.detail) from exc

    @staticmethod
    def _review(
        blueprint: StoryBlueprint,
        opening_facts: Mapping[str, object],
        critics: Sequence[BlueprintCritic],
    ) -> tuple[BlueprintCriticResult, ...]:
        return tuple(critic.critique(blueprint, opening_facts) for critic in critics)
