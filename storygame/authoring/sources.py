"""Immutable raw-source selection for the offline causal-story compiler."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from storygame.authoring.compiler import CompilationError


class _SourceContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StoryBrief(_SourceContract):
    """Author-owned, non-runtime input for a single offline compilation."""

    schema_version: Literal["freytag-story-brief-v1"]
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=80)
    genre: str = Field(min_length=1, max_length=80)
    profile: str = Field(min_length=1, max_length=80)
    premise: str = Field(min_length=1, max_length=4000)
    opening_public_boundary: str = Field(min_length=1, max_length=4000)
    world_notes: tuple[str, ...] = Field(default=(), max_length=64)
    cast_notes: tuple[str, ...] = Field(default=(), max_length=64)
    hard_truths: tuple[str, ...] = Field(default=(), max_length=64)
    protections: tuple[str, ...] = Field(default=(), max_length=64)
    ending_constraints: tuple[str, ...] = Field(default=(), max_length=64)
    dramatic_beats: tuple[str, ...] = Field(default=(), max_length=64)
    possibility_library: tuple[str, ...] = Field(default=(), max_length=64)
    author_notes: tuple[str, ...] = Field(default=(), max_length=64)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _namespaced_extensions(self) -> StoryBrief:
        if any("." not in key for key in self.extensions):
            raise ValueError("extensions keys must be namespaced (for example, 'author.theme')")
        return self


class StoryOutline(_SourceContract):
    id: str | int
    genre: str = Field(min_length=1, max_length=80)
    outline: str = Field(min_length=1)
    tone: str | None = Field(default=None, min_length=1, max_length=80)
    variant: str | None = Field(default=None, min_length=1, max_length=80)
    authoring_only: bool = False
    opening_public_boundary: str = Field(default="", max_length=4000)
    terminal_constraints: tuple[str, ...] = Field(default=(), max_length=64)


class NormalizedStorySource(_SourceContract):
    """The one immutable compiler input contract, never a runtime contract."""

    source_format: Literal["story-outline-inventory-v1", "freytag-story-brief-v1"]
    source_id: str = Field(min_length=1, max_length=120)
    genre: str = Field(min_length=1, max_length=80)
    profile: str = Field(min_length=1, max_length=80)
    source_path: str = Field(min_length=1)
    source_schema_version: str = Field(min_length=1, max_length=80)
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    authoring_only: bool = False
    premise: str = Field(min_length=1)
    opening_public_boundary: str = ""
    hard_constraints: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    creative_direction: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    extensions: dict[str, Any] = Field(default_factory=dict)

    def provenance(self) -> dict[str, str]:
        return {
            "source_format": self.source_format,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "source_schema_version": self.source_schema_version,
            "source_hash": self.source_hash,
        }


def _hash(value: object) -> str:
    return hashlib.sha256(yaml.safe_dump(value, sort_keys=True, allow_unicode=True).encode()).hexdigest()


def _load_yaml(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompilationError("SOURCE_NOT_FOUND", f"authoring source '{path}' does not exist") from exc
    except yaml.YAMLError as exc:
        raise CompilationError("SOURCE_INVALID", f"authoring source '{path}' is not valid YAML") from exc


class StorySourceLoader:
    """Constructor-injected loader for inventory outlines and standalone briefs."""

    def __init__(self, inventory_path: Path, profile_root: Path) -> None:
        self._inventory_path = inventory_path
        self._profile_root = profile_root

    def list_outlines(self) -> tuple[NormalizedStorySource, ...]:
        """Return the complete immutable inventory with one hash per selected entry."""

        try:
            raw = self._inventory_path.read_bytes()
        except FileNotFoundError as exc:
            raise CompilationError(
                "SOURCE_NOT_FOUND", f"authoring source '{self._inventory_path}' does not exist"
            ) from exc
        cached = self._cached_outlines(self._inventory_path.name, raw)
        return tuple(source.model_copy(deep=True) for source in cached)

    def select_outline(self, outline_id: str) -> NormalizedStorySource:
        matches = [source for source in self.list_outlines() if source.source_id == outline_id]
        if len(matches) != 1:
            raise CompilationError("OUTLINE_NOT_FOUND", f"outline '{outline_id}' does not resolve exactly once")
        return matches[0]

    @staticmethod
    @lru_cache(maxsize=4)
    def _cached_outlines(inventory_name: str, raw: bytes) -> tuple[NormalizedStorySource, ...]:
        try:
            payload = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise CompilationError("SOURCE_INVALID", "authoring source is not valid YAML") from exc
        if not isinstance(payload, Mapping) or not isinstance(payload.get("stories"), list):
            raise CompilationError("SOURCE_INVALID", "outline inventory must contain a stories list")
        sources = tuple(StorySourceLoader._normalize_outline(item, inventory_name) for item in payload["stories"])
        source_ids = [source.source_id for source in sources]
        if len(source_ids) != len(set(source_ids)):
            raise CompilationError("SOURCE_INVALID", "outline inventory contains duplicate IDs")
        return sources

    @staticmethod
    def _normalize_outline(payload: object, inventory_name: str) -> NormalizedStorySource:
        try:
            outline = StoryOutline.model_validate(payload)
        except ValidationError as exc:
            raise CompilationError("SOURCE_INVALID", "outline inventory contains an invalid entry") from exc
        return NormalizedStorySource(
            source_format="story-outline-inventory-v1",
            source_id=str(outline.id),
            genre=outline.genre,
            profile=outline.genre,
            source_path=f"{inventory_name}#{outline.id}",
            source_schema_version="story-outline-inventory-v1",
            source_hash=_hash(payload),
            authoring_only=outline.authoring_only,
            premise=outline.outline,
            opening_public_boundary=outline.opening_public_boundary,
            hard_constraints={"terminal_constraints": outline.terminal_constraints},
            creative_direction={
                key: (value,) for key, value in {"tone": outline.tone, "variant": outline.variant}.items() if value
            },
        )

    def load_brief(self, path: Path) -> NormalizedStorySource:
        payload = _load_yaml(path)
        if not isinstance(payload, Mapping):
            raise CompilationError("SOURCE_INVALID", "Story Brief must be a YAML mapping")
        try:
            brief = StoryBrief.model_validate(payload)
        except ValidationError as exc:
            raise CompilationError("SOURCE_INVALID", f"Story Brief is invalid: {exc.errors()[0]['loc']}") from exc
        self._validate_profile(brief.genre, brief.profile)
        return NormalizedStorySource(
            source_format="freytag-story-brief-v1",
            source_id=brief.id,
            genre=brief.genre,
            profile=brief.profile,
            source_path=path.name,
            source_schema_version=brief.schema_version,
            source_hash=_hash(payload),
            premise=brief.premise,
            opening_public_boundary=brief.opening_public_boundary,
            hard_constraints={
                "hard_truths": brief.hard_truths,
                "protections": brief.protections,
                "ending_constraints": brief.ending_constraints,
            },
            creative_direction={
                "world_notes": brief.world_notes,
                "cast_notes": brief.cast_notes,
                "dramatic_beats": brief.dramatic_beats,
                "possibility_library": brief.possibility_library,
                "author_notes": brief.author_notes,
            },
            extensions=brief.extensions,
        )

    def _validate_profile(self, genre: str, profile: str) -> None:
        profile_path = self._profile_root / f"{profile}.yaml"
        if not profile_path.is_file():
            raise CompilationError("PROFILE_NOT_FOUND", f"profile '{profile}' is not available")
        payload = _load_yaml(profile_path)
        if not isinstance(payload, Mapping) or payload.get("genre") != genre:
            raise CompilationError("PROFILE_MISMATCH", f"profile '{profile}' does not declare genre '{genre}'")
