"""Data-driven causal profile validation for ``story-blueprint-v2``."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from storygame.authoring.bound_ir import BoundBlueprint, bind_blueprint
from storygame.authoring.causal_contracts import CausalCompiledStory, CausalValidationError


class _Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RoleRequirement(_Profile):
    role: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    min_count: int = Field(default=1, ge=1, le=64)


class CausalProfile(_Profile):
    schema_version: Literal["causal-profile-v2"] = "causal-profile-v2"
    profile_version: int = Field(ge=1, le=9999)
    genre: str = Field(min_length=1, max_length=80)
    terminal_roles: tuple[RoleRequirement, ...] = Field(min_length=1, max_length=64)
    causal_roles: tuple[RoleRequirement, ...] = Field(min_length=1, max_length=64)
    minimum_independent_proof_routes: int = Field(default=2, ge=1, le=16)
    minimum_alternative_suspects: int = Field(default=0, ge=0, le=16)
    allowed_opportunity_types: tuple[str, ...] = Field(min_length=1, max_length=64)
    required_freytag_phases: tuple[str, ...] = Field(min_length=1, max_length=16)
    minimum_storylet_variety: int = Field(default=0, ge=0, le=16)
    maximum_unbroken_pressure_span: int = Field(default=100, ge=1, le=100)
    minimum_alternate_progression_paths: int = Field(default=0, ge=0, le=16)
    minimum_initial_social_contacts: int = Field(default=1, ge=0, le=64)
    minimum_evidence_route_diversity: int = Field(default=2, ge=0, le=16)
    minimum_conversational_route_diversity: int = Field(default=2, ge=1, le=16)
    minimum_interaction_agency_modes: int = Field(default=2, ge=1, le=5)


class CausalProfileRegistry:
    def __init__(self, profiles: Mapping[str, CausalProfile]) -> None:
        self._profiles = dict(profiles)

    @classmethod
    def from_directory(cls, root: Path) -> CausalProfileRegistry:
        profiles: dict[str, CausalProfile] = {}
        for path in sorted(root.glob("*.yaml")):
            try:
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
                profile = CausalProfile.model_validate(payload)
            except (OSError, ValidationError, yaml.YAMLError) as exc:
                raise CausalValidationError("PROFILE_INVALID", str(path)) from exc
            if path.stem in profiles:
                raise CausalValidationError("PROFILE_DUPLICATE", path.stem)
            profiles[path.stem] = profile
        return cls(profiles)

    def resolve(self, profile_id: str) -> CausalProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as exc:
            raise CausalValidationError("PROFILE_NOT_FOUND", profile_id) from exc

    def validate(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCompiledStory:
        bound = story if isinstance(story, BoundBlueprint) else bind_blueprint(story)
        candidate = bound.story
        profile = self.resolve(candidate.profile)
        if profile.genre != candidate.genre:
            raise CausalValidationError("PROFILE_MISMATCH", f"profile '{candidate.profile}' is not '{candidate.genre}'")
        kinds = {item.kind for item in bound.evidence_opportunities}
        if not kinds <= set(profile.allowed_opportunity_types):
            raise CausalValidationError("OPPORTUNITY_TYPE_INVALID", "opportunity type is not allowed by profile")
        phases = {beat.declaration.phase for beat in bound.required_beats}
        missing = set(profile.required_freytag_phases) - phases
        if missing:
            raise CausalValidationError("FREYTAG_GATE_REQUIRED", f"missing phases: {', '.join(sorted(missing))}")
        for requirement in (*profile.terminal_roles, *profile.causal_roles):
            count = sum(requirement.role in truth.declaration.roles for truth in bound.truths)
            if count < requirement.min_count:
                raise CausalValidationError("CAUSAL_ROLE_REQUIRED", f"missing '{requirement.role}'")
        if len(bound.hypotheses) < profile.minimum_alternative_suspects:
            raise CausalValidationError(
                "ALTERNATIVE_SUSPECTS_REQUIRED",
                f"requires {profile.minimum_alternative_suspects} plausible alternative suspects",
            )
        storylets = candidate.storylets
        if storylets and len({item.purpose for item in storylets}) < profile.minimum_storylet_variety:
            raise CausalValidationError("STORYLET_VARIETY_REQUIRED", "storylet purposes do not meet profile minimum")
        pressure_span = max(
            (item.availability.pressure.maximum - item.availability.pressure.minimum for item in storylets), default=0
        )
        if storylets and pressure_span > profile.maximum_unbroken_pressure_span:
            raise CausalValidationError("STORYLET_PRESSURE_SPAN", "storylet pressure span exceeds profile maximum")
        alternate_paths = sum(bool(item.failure_forward_storylet_ids) for item in storylets)
        if storylets and alternate_paths < profile.minimum_alternate_progression_paths:
            raise CausalValidationError(
                "STORYLET_ALTERNATES_REQUIRED", "storylets do not meet alternate progression minimum"
            )
        if bound.evidence_realizations:
            initial_locations = {item.id for item in bound.locations if item.declaration.initial_access}
            contacts = sum(
                participant.declaration.initial_availability == "present"
                and participant.declaration.initial_location_id in initial_locations
                for participant in bound.participants
            )
            if contacts < profile.minimum_initial_social_contacts:
                raise CausalValidationError(
                    "INITIAL_SOCIAL_CONTACTS_REQUIRED",
                    f"requires {profile.minimum_initial_social_contacts} present opening contacts",
                )
            diversity = len({item.declaration.kind for item in bound.evidence_realizations})
            if diversity < profile.minimum_evidence_route_diversity:
                raise CausalValidationError(
                    "EVIDENCE_ROUTE_DIVERSITY_REQUIRED",
                    f"requires {profile.minimum_evidence_route_diversity} evidence realization kinds",
                )
        if bound.interaction_frames:
            if any(
                len(set(item.declaration.allowed_tactics)) < profile.minimum_conversational_route_diversity
                for item in bound.interaction_frames
            ):
                raise CausalValidationError(
                    "CONVERSATIONAL_ROUTE_DIVERSITY_REQUIRED",
                    f"requires {profile.minimum_conversational_route_diversity} tactics per interaction",
                )
            if any(
                len(set(item.declaration.agency_modes)) < profile.minimum_interaction_agency_modes
                for item in bound.interaction_frames
            ):
                raise CausalValidationError(
                    "INTERACTION_AGENCY_REQUIRED",
                    f"requires {profile.minimum_interaction_agency_modes} player agency modes per interaction",
                )
        return candidate
