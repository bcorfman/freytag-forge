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


class OpeningContact(_Contract):
    """A declared person who is present and addressable at session start."""

    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    relationship: str = Field(min_length=1, max_length=160)
    location: str = Field(pattern=_ID_PATTERN, max_length=80)
    public_knowledge: tuple[str, ...] = Field(default=(), max_length=32)
    item_custody: tuple[str, ...] = Field(default=(), max_length=32)


class OpeningMetadata(_Contract):
    """Spoiler-safe orientation data emitted by the authoring compiler."""

    scene: str = Field(min_length=1, max_length=1200)
    protagonist_context: str = Field(min_length=1, max_length=1200)
    arrival_context: str = Field(min_length=1, max_length=1200)
    public_briefing: tuple[str, ...] = Field(min_length=1, max_length=32)
    scene_purpose: str = Field(min_length=1, max_length=1200)
    contacts: tuple[OpeningContact, ...] = Field(default=(), max_length=16)
    first_available_actions: tuple[str, ...] = Field(min_length=1, max_length=16)


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


class ReadableDocument(_Contract):
    """Package-declared disclosure routes for a readable item."""

    item_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    discovery_key: str = Field(pattern=_ID_PATTERN, max_length=80)
    knowledge: tuple[str, ...] = Field(default=(), max_length=32)
    npc_disclosures: dict[str, tuple[str, ...]] = Field(default_factory=dict, max_length=32)
    leads: tuple[str, ...] = Field(default=(), max_length=16)


class ItemDefinition(_Contract):
    """Generic item affordances and initial custody."""

    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1200)
    affordances: tuple[str, ...] = Field(default=("examine", "take", "use"), max_length=16)
    portable: bool = True
    initial_holder: str = Field(min_length=1, max_length=120)
    readable: ReadableDocument | None = None


class CompiledStory(_Contract):
    schema_version: Literal["compiled-story-v1"]
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    version: int = Field(ge=1, le=9999)
    genre: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    premise: str = Field(min_length=1, max_length=1200)
    opening: OpeningMetadata | None = None
    central_question: str = Field(min_length=1, max_length=500)
    initial_world_state: dict[str, Any] = Field(default_factory=dict)
    characters: tuple[Character, ...] = Field(min_length=1, max_length=32)
    beats: tuple[Beat, ...] = Field(max_length=32)
    protected_revelations: tuple[ProtectedRevelation, ...] = Field(default=(), max_length=32)
    item_definitions: tuple[ItemDefinition, ...] = Field(default=(), max_length=64)
    readable_documents: tuple[ReadableDocument, ...] = Field(default=(), max_length=64)
