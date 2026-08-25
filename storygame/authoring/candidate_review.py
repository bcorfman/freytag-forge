"""Explicit human review and immutable promotion for causal-story candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from storygame.authoring.blueprint_compiler import BlueprintCompilation
from storygame.authoring.causal_contracts import (
    CausalCompiledStory,
    CausalValidationError,
    validate_causal_compiled_story,
)
from storygame.authoring.causal_critics import CausalCompletenessCritic, FreytagProgressionCritic, RouteFairnessCritic
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from storygame.authoring.storylet_critics import (
    DramaticEscalationCritic,
    FailureForwardViabilityCritic,
    ParticipantContinuityCritic,
    ProtectedKnowledgeSafetyCritic,
    StoryletCoverageCritic,
)

_BASE_REVIEW_CHECKLIST = frozenset(
    {
        "terminal_roles",
        "knowledge_boundaries",
        "route_diversity",
        "failure_forward",
        "map_and_custody",
    }
)
_STORYLET_REVIEW_CHECKLIST = frozenset(
    {
        "dramatic_questions",
        "participant_agency",
        "repeated_content_risk",
        "consequence_quality",
        "distinct_progression_paths",
    }
)


class CandidateReview(BaseModel):
    """A human's explicit approval of one locally valid candidate."""

    model_config = ConfigDict(frozen=True)

    reviewer: str = Field(min_length=1, max_length=160)
    approved: bool
    checklist: tuple[str, ...]
    notes: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def _complete_approval(self) -> CandidateReview:
        if self.approved and not set(self.checklist) >= _BASE_REVIEW_CHECKLIST:
            missing = ", ".join(sorted(_BASE_REVIEW_CHECKLIST - set(self.checklist)))
            raise ValueError(f"approved review is missing checklist items: {missing}")
        return self


class ReviewedCausalStory(BaseModel):
    """A hash-bound, immutable promotion record; never runtime state."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["reviewed-story-blueprint-v2"]
    candidate_filename: str = Field(min_length=1, max_length=160)
    candidate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    review: CandidateReview
    story: CausalCompiledStory


def promote_candidate(
    candidate_path: Path,
    output_path: Path,
    review: CandidateReview,
    profiles: CausalProfileRegistry,
) -> ReviewedCausalStory:
    """Revalidate and promote an approved candidate without modifying either input."""

    if not review.approved:
        raise CompilationError("REVIEW_NOT_APPROVED", "a reviewed artifact requires explicit human approval")
    if output_path.exists():
        raise CompilationError("REVIEWED_OUTPUT_EXISTS", "reviewed artifacts never overwrite an existing file")
    compilation, raw_candidate = _load_candidate(candidate_path)
    if not compilation.accepted:
        raise CompilationError("CANDIDATE_NOT_ACCEPTED", "locally rejected candidates cannot be promoted")
    if compilation.story.provenance.generation_mode == "debug":
        raise CompilationError("DEBUG_CANDIDATE_NOT_PROMOTABLE", "debug compilation candidates cannot be promoted")
    _require_storylet_review(review, compilation.story)
    story = _revalidate(compilation.story, profiles)
    artifact = ReviewedCausalStory(
        schema_version="reviewed-story-blueprint-v2",
        candidate_filename=candidate_path.name,
        candidate_sha256=hashlib.sha256(raw_candidate).hexdigest(),
        review=review,
        story=story,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    if temporary.exists():
        raise CompilationError("REVIEWED_OUTPUT_TEMP_EXISTS", "remove the previous incomplete reviewed-artifact write")
    temporary.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(output_path)
    return artifact


def autopromote_candidate(
    candidate_path: Path, output_path: Path, profiles: CausalProfileRegistry
) -> ReviewedCausalStory:
    """Create the runtime artifact for an accepted non-debug compiler result."""

    return promote_candidate(
        candidate_path,
        output_path,
        CandidateReview(
            reviewer="compiler",
            approved=True,
            checklist=required_review_checklist(),
            notes="Automatically promoted after deterministic compiler validation and critic checks.",
        ),
        profiles,
    )


def required_review_checklist() -> tuple[str, ...]:
    """Return stable checklist IDs for the review CLI and operator documentation."""

    return tuple(sorted(_BASE_REVIEW_CHECKLIST | _STORYLET_REVIEW_CHECKLIST))


def _require_storylet_review(review: CandidateReview, story: CausalCompiledStory) -> None:
    if story.dramatic_spine is None and not story.storylets:
        return
    missing = _STORYLET_REVIEW_CHECKLIST - set(review.checklist)
    if missing:
        detail = "approved review is missing checklist items: " + ", ".join(sorted(missing))
        raise CompilationError("REVIEW_NOT_APPROVED", detail)


def _load_candidate(path: Path) -> tuple[BlueprintCompilation, bytes]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise CompilationError("CANDIDATE_NOT_FOUND", f"candidate '{path.name}' does not exist") from exc
    try:
        payload = json.loads(raw)
        return BlueprintCompilation.model_validate(payload), raw
    except (json.JSONDecodeError, ValidationError) as exc:
        raise CompilationError("CANDIDATE_REVIEW_INVALID", f"candidate '{path.name}' has an invalid envelope") from exc


def _revalidate(story: CausalCompiledStory, profiles: CausalProfileRegistry) -> CausalCompiledStory:
    try:
        validated = validate_causal_compiled_story(story)
        profiles.validate(validated)
    except CausalValidationError as exc:
        raise CompilationError("CANDIDATE_REVIEW_INVALID", str(exc)) from exc
    diagnostics = tuple(
        detail
        for critic in (
            CausalCompletenessCritic(),
            RouteFairnessCritic(profiles),
            FreytagProgressionCritic(profiles),
            StoryletCoverageCritic(profiles),
            DramaticEscalationCritic(),
            ParticipantContinuityCritic(),
            ProtectedKnowledgeSafetyCritic(),
            FailureForwardViabilityCritic(),
        )
        for detail in critic.critique(validated).diagnostics
    )
    if diagnostics:
        raise CompilationError("CANDIDATE_REVIEW_INVALID", "; ".join(diagnostics))
    return validated
