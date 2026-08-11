"""Immutable V2 authoring contracts. These are not runtime state contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_ID_PATTERN = r"^[a-z][a-z0-9_]*$"


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Character(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)


class CompletionTag(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    description: str = Field(min_length=1, max_length=300)


class BeatPacing(_Contract):
    nudge_after: int = Field(ge=1, le=100)
    advance_after: int = Field(ge=1, le=100)
    escalate_after: int = Field(ge=1, le=100)
    force_consequence_after: int = Field(ge=1, le=100)


class ProtectedRevelation(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=500)
    reveal_after: tuple[str, ...] = Field(min_length=1, max_length=16)


class Beat(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    phase: Literal["setup", "rising_action", "crisis", "climax", "resolution"]
    summary: str = Field(min_length=1, max_length=600)
    required: bool = True
    prerequisites: tuple[str, ...] = Field(default=(), max_length=16)
    unlocks: tuple[str, ...] = Field(default=(), max_length=16)
    completion_tags: tuple[CompletionTag, ...] = Field(default=(), max_length=16)
    pacing: BeatPacing
    answers_central_question: bool = False


class CompiledStory(_Contract):
    schema_version: Literal["compiled-story-v1"]
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    version: int = Field(ge=1, le=9999)
    genre: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    premise: str = Field(min_length=1, max_length=1200)
    central_question: str = Field(min_length=1, max_length=500)
    initial_world_state: dict[str, Any] = Field(default_factory=dict)
    characters: tuple[Character, ...] = Field(min_length=1, max_length=32)
    beats: tuple[Beat, ...] = Field(max_length=32)
    protected_revelations: tuple[ProtectedRevelation, ...] = Field(default=(), max_length=32)
