"""Declarative, injected genre validation for immutable Story Blueprints."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from storygame.authoring.blueprint_contracts import BlueprintValidationError, StoryBlueprint, validate_story_blueprint


class _ProfileContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CausalRoleRequirement(_ProfileContract):
    role: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    min_count: int = Field(default=1, ge=0, le=64)
    max_count: int = Field(default=1, ge=1, le=64)


class TurningPoint(_ProfileContract):
    role: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    phase: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class EvidenceRequirement(_ProfileContract):
    revelation_role: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    subject_role: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    route_roles: tuple[str, ...] = Field(min_length=1, max_length=16)


class GenreProfile(_ProfileContract):
    schema_version: str = "genre-profile-v1"
    profile_version: int = Field(ge=1, le=9999)
    genre: str = Field(min_length=1, max_length=80)
    causal_roles: tuple[CausalRoleRequirement, ...] = Field(min_length=1, max_length=64)
    allowed_revelation_roles: tuple[str, ...] = Field(min_length=1, max_length=64)
    phase_order: tuple[str, ...] = Field(min_length=1, max_length=16)
    turning_points: tuple[TurningPoint, ...] = Field(min_length=1, max_length=16)
    ending_truth_roles: tuple[str, ...] = Field(default=(), max_length=32)
    evidence_requirements: tuple[EvidenceRequirement, ...] = Field(default=(), max_length=32)
    policy_mappings: Mapping[str, str] = Field(default_factory=dict)


class GenreBlueprintValidator(Protocol):
    """Injected authoring validator; runtime never dispatches on genre names."""

    def validate(self, blueprint: StoryBlueprint) -> StoryBlueprint: ...


class DeclarativeGenreBlueprintValidator:
    """Interprets one profile without embedding any named genre semantics."""

    def __init__(self, profile: GenreProfile) -> None:
        self._profile = profile

    def validate(self, blueprint: StoryBlueprint) -> StoryBlueprint:
        story = validate_story_blueprint(blueprint)
        if story.genre != self._profile.genre:
            raise BlueprintValidationError("GENRE_PROFILE_MISMATCH", f"expected '{self._profile.genre}'")
        bindings = self._validate_causal_roles(story)
        self._validate_revelations(story)
        self._validate_phase_order(story)
        self._validate_turning_points(story)
        self._validate_endings(story, bindings)
        self._validate_evidence(story, bindings)
        self._validate_climax(story)
        return story

    def _validate_causal_roles(self, story: StoryBlueprint) -> dict[str, tuple[str, ...]]:
        bindings: dict[str, list[str]] = {}
        for binding in story.genre_causality:
            bindings.setdefault(binding.role, []).append(binding.truth_id)
        for requirement in self._profile.causal_roles:
            count = len(bindings.get(requirement.role, []))
            if count < requirement.min_count:
                raise BlueprintValidationError("GENRE_CAUSAL_ROLE_REQUIRED", f"missing '{requirement.role}'")
            if count > requirement.max_count:
                raise BlueprintValidationError("GENRE_CAUSAL_ROLE_CARDINALITY", f"too many '{requirement.role}'")
        return {role: tuple(truths) for role, truths in bindings.items()}

    def _validate_revelations(self, story: StoryBlueprint) -> None:
        allowed = set(self._profile.allowed_revelation_roles)
        for revelation in story.revelations:
            if revelation.role not in allowed:
                raise BlueprintValidationError("REVELATION_ROLE_INVALID", f"'{revelation.role}' is not allowed")
        for route in story.realization_routes:
            revelation = next(item for item in story.revelations if item.id == route.revelation_id)
            if set(route.availability_constraints) & set(revelation.completion_conditions):
                raise BlueprintValidationError("CIRCULAR_PROOF", f"route '{route.id}' needs its own revelation")

    def _validate_phase_order(self, story: StoryBlueprint) -> None:
        positions = {phase: index for index, phase in enumerate(self._profile.phase_order)}
        prior = -1
        for beat in (*story.required_beats, *story.optional_beats):
            if beat.phase not in positions or positions[beat.phase] < prior:
                raise BlueprintValidationError("PHASE_ORDER_INVALID", f"beat '{beat.id}' has phase '{beat.phase}'")
            prior = positions[beat.phase]

    def _validate_turning_points(self, story: StoryBlueprint) -> None:
        beats = (*story.required_beats, *story.optional_beats)
        for turning_point in self._profile.turning_points:
            if not any(beat.role == turning_point.role and beat.phase == turning_point.phase for beat in beats):
                raise BlueprintValidationError(
                    "TURNING_POINT_REQUIRED", f"missing {turning_point.role} in {turning_point.phase}"
                )

    def _validate_endings(self, story: StoryBlueprint, bindings: Mapping[str, Sequence[str]]) -> None:
        required_truths = {truth for role in self._profile.ending_truth_roles for truth in bindings.get(role, ())}
        for ending in story.end_states:
            if not required_truths <= set(ending.required_truths):
                raise BlueprintValidationError("GENRE_ENDING_INVALID", f"end state '{ending.id}' omits genre truth")

    def _validate_evidence(self, story: StoryBlueprint, bindings: Mapping[str, Sequence[str]]) -> None:
        routes = {route.revelation_id: [] for route in story.realization_routes}
        for route in story.realization_routes:
            routes[route.revelation_id].append(route)
        for requirement in self._profile.evidence_requirements:
            if not bindings.get(requirement.subject_role):
                continue
            matched = [
                revelation
                for revelation in story.revelations
                if revelation.role == requirement.revelation_role
                and revelation.subject_role == requirement.subject_role
            ]
            if not any(any(route.role in requirement.route_roles for route in routes[item.id]) for item in matched):
                raise BlueprintValidationError(
                    "EVIDENCE_ROUTE_REQUIRED",
                    f"'{requirement.revelation_role}' lacks evidence for '{requirement.subject_role}'",
                )

    def _validate_climax(self, story: StoryBlueprint) -> None:
        if self._profile.policy_mappings.get("climax_requires_required_discoveries") != "true":
            return
        required = {item.id for item in story.revelations if item.required}
        for beat in story.required_beats:
            unsupported = not beat.revelation_dependencies or not set(beat.revelation_dependencies) <= required
            if beat.role == "climax" and unsupported:
                raise BlueprintValidationError("CLIMAX_UNSUPPORTED", f"climax '{beat.id}' lacks required discoveries")


class GenreProfileRegistry:
    """Explicit registry composed at the authoring boundary through injection."""

    def __init__(self, validators: Mapping[str, GenreBlueprintValidator]) -> None:
        self._validators = dict(validators)

    @classmethod
    def from_directory(cls, root: Path | None = None) -> GenreProfileRegistry:
        directory = root or Path("data/genre_profiles")
        validators: dict[str, GenreBlueprintValidator] = {}
        for path in sorted(directory.glob("*.yaml")):
            try:
                profile = GenreProfile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
            except (OSError, ValidationError, yaml.YAMLError) as exc:
                raise BlueprintValidationError("GENRE_PROFILE_INVALID", str(path)) from exc
            if profile.genre in validators:
                raise BlueprintValidationError("GENRE_PROFILE_DUPLICATE", profile.genre)
            validators[profile.genre] = DeclarativeGenreBlueprintValidator(profile)
        return cls(validators)

    def resolve(self, genre: str) -> GenreBlueprintValidator:
        try:
            return self._validators[genre]
        except KeyError as exc:
            raise BlueprintValidationError("GENRE_PROFILE_NOT_FOUND", genre) from exc

    def validate(self, blueprint: StoryBlueprint) -> StoryBlueprint:
        return self.resolve(blueprint.genre).validate(blueprint)
