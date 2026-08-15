"""Immutable, story-agnostic contracts for offline Story Blueprint authoring."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_ID_PATTERN = r"^[a-z][a-z0-9_]*$"


class BlueprintValidationError(ValueError):
    """A local semantic validation failure in an immutable blueprint."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class _BlueprintContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceOutlineProvenance(_BlueprintContract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class CanonicalTruth(_BlueprintContract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=600)


class GenreCausality(_BlueprintContract):
    """A profile-defined semantic role bound to one canonical truth."""

    role: str = Field(pattern=_ID_PATTERN, max_length=80)
    truth_id: str = Field(pattern=_ID_PATTERN, max_length=80)


class ProtectedFact(_BlueprintContract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    truth_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    release_after: tuple[str, ...] = Field(min_length=1, max_length=16)


class Revelation(_BlueprintContract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    role: str = Field(default="discovery", pattern=_ID_PATTERN, max_length=80)
    subject_role: str | None = Field(default=None, pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    prerequisite_truths: tuple[str, ...] = Field(default=(), max_length=16)
    prerequisite_revelations: tuple[str, ...] = Field(default=(), max_length=16)
    completion_conditions: tuple[str, ...] = Field(min_length=1, max_length=16)
    protected_facts: tuple[str, ...] = Field(default=(), max_length=16)
    unlocks: tuple[str, ...] = Field(default=(), max_length=16)
    required: bool = True


class RouteSatisfier(_BlueprintContract):
    truth_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    operator: Literal["establish", "retract"]


class FailureForward(_BlueprintContract):
    result_truths: tuple[str, ...] = Field(min_length=1, max_length=16)
    unlocks: tuple[str, ...] = Field(default=(), max_length=16)


class RealizationRoute(_BlueprintContract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    revelation_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    role: str = Field(min_length=1, max_length=80)
    satisfiers: tuple[RouteSatisfier, ...] = Field(min_length=1, max_length=16)
    availability_constraints: tuple[str, ...] = Field(default=(), max_length=16)
    failure_forward: FailureForward


class DramaticBeat(_BlueprintContract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    phase: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=80)
    question: str | None = Field(default=None, min_length=1, max_length=500)
    required_outcome: str | None = Field(default=None, pattern=_ID_PATTERN, max_length=80)
    narrative_function: str | None = Field(default=None, min_length=1, max_length=600)
    revelation_dependencies: tuple[str, ...] = Field(default=(), max_length=16)
    pressure_change: int = Field(ge=-10, le=10)
    pacing: int = Field(ge=0, le=100)
    optional_purpose: Literal["alternative_satisfier", "complication", "development"] | None = None


class OppositionClock(_BlueprintContract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    opportunity_decay: int = Field(ge=0, le=100)
    max_ticks: int = Field(ge=1, le=1000)


class EndState(_BlueprintContract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    required_truths: tuple[str, ...] = Field(min_length=1, max_length=32)
    required_revelations: tuple[str, ...] = Field(default=(), max_length=32)
    answers_central_question: bool = False


class StoryBlueprint(_BlueprintContract):
    schema_version: Literal["story-blueprint-v1"]
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    version: int = Field(ge=1, le=9999)
    source_outline: SourceOutlineProvenance
    genre: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    premise: str = Field(min_length=1, max_length=1200)
    central_question: str = Field(min_length=1, max_length=500)
    canonical_truths: tuple[CanonicalTruth, ...] = Field(min_length=1, max_length=128)
    genre_causality: tuple[GenreCausality, ...] = Field(default=(), max_length=64)
    protected_facts: tuple[ProtectedFact, ...] = Field(default=(), max_length=64)
    revelations: tuple[Revelation, ...] = Field(min_length=1, max_length=64)
    realization_routes: tuple[RealizationRoute, ...] = Field(min_length=1, max_length=128)
    required_beats: tuple[DramaticBeat, ...] = Field(min_length=1, max_length=64)
    optional_beats: tuple[DramaticBeat, ...] = Field(default=(), max_length=64)
    opposition_clocks: tuple[OppositionClock, ...] = Field(default=(), max_length=32)
    end_states: tuple[EndState, ...] = Field(min_length=1, max_length=16)


def _ids(values: Iterable[object], category: str) -> set[str]:
    seen: set[str] = set()
    for value in values:
        identifier = value.id  # type: ignore[attr-defined]
        if identifier in seen:
            raise BlueprintValidationError("DUPLICATE_ID", f"duplicate {category} id '{identifier}'")
        seen.add(identifier)
    return seen


def _references(values: Iterable[str], known: set[str], source: str) -> None:
    for reference in values:
        if reference not in known:
            raise BlueprintValidationError("UNKNOWN_REFERENCE", f"{source} references unknown '{reference}'")


def _validate_revelation_graph(story: StoryBlueprint, truth_ids: set[str], protected_ids: set[str]) -> None:
    revelation_ids = _ids(story.revelations, "revelation")
    by_id = {revelation.id: revelation for revelation in story.revelations}
    for revelation in story.revelations:
        _references(revelation.prerequisite_truths, truth_ids, f"revelation '{revelation.id}'")
        _references(revelation.completion_conditions, truth_ids, f"revelation '{revelation.id}'")
        _references(revelation.protected_facts, protected_ids, f"revelation '{revelation.id}'")
        _references(
            (*revelation.prerequisite_revelations, *revelation.unlocks),
            revelation_ids,
            f"revelation '{revelation.id}'",
        )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(revelation_id: str) -> None:
        if revelation_id in visiting:
            raise BlueprintValidationError("REVELATION_CYCLE", f"revelation graph contains '{revelation_id}'")
        if revelation_id in visited:
            return
        visiting.add(revelation_id)
        for prerequisite in by_id[revelation_id].prerequisite_revelations:
            visit(prerequisite)
        visiting.remove(revelation_id)
        visited.add(revelation_id)

    for revelation_id in revelation_ids:
        visit(revelation_id)


def _validate_routes(story: StoryBlueprint, truth_ids: set[str], revelation_ids: set[str]) -> None:
    _ids(story.realization_routes, "realization route")
    revelations_by_id = {revelation.id: revelation for revelation in story.revelations}
    for route in story.realization_routes:
        _references((route.revelation_id,), revelation_ids, f"route '{route.id}'")
        _references(route.availability_constraints, truth_ids, f"route '{route.id}'")
        _references((item.truth_id for item in route.satisfiers), truth_ids, f"route '{route.id}'")
        _references(route.failure_forward.result_truths, truth_ids, f"route '{route.id}' failure-forward")
        _references(route.failure_forward.unlocks, revelation_ids, f"route '{route.id}' failure-forward")
        route_results = {satisfier.truth_id for satisfier in route.satisfiers if satisfier.operator == "establish"}
        route_results.update(route.failure_forward.result_truths)
        completion_conditions = revelations_by_id[route.revelation_id].completion_conditions
        if not set(completion_conditions) <= route_results:
            raise BlueprintValidationError(
                "ROUTE_DOES_NOT_SATISFY_REVELATION",
                f"route '{route.id}' cannot complete revelation '{route.revelation_id}'",
            )
    routed = {route.revelation_id for route in story.realization_routes}
    for revelation in story.revelations:
        if revelation.required and revelation.id not in routed:
            raise BlueprintValidationError(
                "UNREACHABLE_REVELATION", f"required revelation '{revelation.id}' has no route"
            )


def _validate_beats(story: StoryBlueprint, truth_ids: set[str], revelation_ids: set[str]) -> None:
    required_ids = _ids(story.required_beats, "required beat")
    optional_ids = _ids(story.optional_beats, "optional beat")
    if required_ids & optional_ids:
        raise BlueprintValidationError("DUPLICATE_ID", "a beat cannot be both required and optional")
    required_outcomes = {beat.required_outcome for beat in story.required_beats if beat.required_outcome}
    for beat in (*story.required_beats, *story.optional_beats):
        _references(beat.revelation_dependencies, revelation_ids, f"beat '{beat.id}'")
        if beat.required_outcome:
            _references((beat.required_outcome,), truth_ids, f"beat '{beat.id}'")
    for beat in story.required_beats:
        if not beat.required_outcome or not beat.question:
            raise BlueprintValidationError(
                "REQUIRED_BEAT_INCOMPLETE", f"required beat '{beat.id}' needs question and outcome"
            )
    for beat in story.optional_beats:
        if beat.optional_purpose is None:
            raise BlueprintValidationError("OPTIONAL_PURPOSE_REQUIRED", f"optional beat '{beat.id}' needs a purpose")
        if beat.optional_purpose == "alternative_satisfier":
            if not beat.required_outcome or beat.required_outcome not in required_outcomes:
                raise BlueprintValidationError(
                    "OPTIONAL_ONLY_REQUIRED_OUTCOME",
                    f"optional beat '{beat.id}' cannot be the only satisfier for '{beat.required_outcome}'",
                )
        elif not beat.narrative_function:
            raise BlueprintValidationError(
                "OPTIONAL_BEAT_INCOMPLETE", f"optional beat '{beat.id}' needs a narrative function"
            )


def _validate_endings(story: StoryBlueprint, truth_ids: set[str], revelation_ids: set[str]) -> None:
    _ids(story.end_states, "end state")
    required_revelations = {revelation.id for revelation in story.revelations if revelation.required}
    for ending in story.end_states:
        _references(ending.required_truths, truth_ids, f"end state '{ending.id}'")
        _references(ending.required_revelations, revelation_ids, f"end state '{ending.id}'")
        if not required_revelations <= set(ending.required_revelations):
            raise BlueprintValidationError("ENDING_NOT_VIABLE", f"end state '{ending.id}' omits a required revelation")
    if not any(ending.answers_central_question for ending in story.end_states):
        raise BlueprintValidationError(
            "CENTRAL_QUESTION_UNANSWERED", "at least one end state must answer the central question"
        )


def validate_story_blueprint(payload: Mapping[str, object] | StoryBlueprint) -> StoryBlueprint:
    """Parse and validate a generic blueprint before any bootstrap realization."""

    try:
        story = payload if isinstance(payload, StoryBlueprint) else StoryBlueprint.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        path = ".".join(str(part) for part in first["loc"])
        raise BlueprintValidationError("CONTRACT_INVALID", f"{path}: {first['type']}") from exc
    truth_ids = _ids(story.canonical_truths, "canonical truth")
    roles = [binding.role for binding in story.genre_causality]
    if len(roles) != len(set(roles)):
        raise BlueprintValidationError("DUPLICATE_ID", "duplicate genre causal role")
    _references((binding.truth_id for binding in story.genre_causality), truth_ids, "genre causality")
    protected_ids = _ids(story.protected_facts, "protected fact")
    revelation_ids = {revelation.id for revelation in story.revelations}
    for protected in story.protected_facts:
        _references((protected.truth_id,), truth_ids, f"protected fact '{protected.id}'")
        _references(protected.release_after, revelation_ids, f"protected fact '{protected.id}'")
    _validate_revelation_graph(story, truth_ids, protected_ids)
    _validate_routes(story, truth_ids, revelation_ids)
    _validate_beats(story, truth_ids, revelation_ids)
    _ids(story.opposition_clocks, "opposition clock")
    _validate_endings(story, truth_ids, revelation_ids)
    return story


def load_story_blueprint_fixture(genre: str, root: Path | None = None) -> StoryBlueprint:
    """Load a checked-in Phase-1 blueprint fixture without making it runtime state."""

    fixture_root = root or Path("data/story_blueprints/v1")
    path = fixture_root / f"{genre}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BlueprintValidationError("FIXTURE_NOT_FOUND", f"blueprint fixture '{genre}' does not exist") from exc
    except json.JSONDecodeError as exc:
        raise BlueprintValidationError("FIXTURE_INVALID", f"blueprint fixture '{genre}' is not JSON") from exc
    return validate_story_blueprint(payload)
