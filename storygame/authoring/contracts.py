"""Immutable V2 authoring contracts. These are not runtime state contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    player_context: str | None = Field(default=None, max_length=1200)
    companions: tuple[str, ...] = Field(default=(), max_length=16)
    situation: str | None = Field(default=None, max_length=1600)
    next_steps: tuple[str, ...] = Field(default=(), max_length=16)


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


class FactDeclaration(_Contract):
    """A package-declared fact that can be seeded by the runtime."""

    predicate: str = Field(pattern=_ID_PATTERN, max_length=64)
    subject: str = Field(min_length=1, max_length=120)
    object: str | None = Field(default=None, max_length=120)
    value: str | None = Field(default=None, max_length=1200)


class GoalDeclaration(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    required: bool = True


class TaskDeclaration(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    goal_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    initial_status: Literal["available", "active", "blocked"] = "available"


class ClueDeclaration(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    fact_ids: tuple[str, ...] = Field(default=(), max_length=16)


class RelationshipDeclaration(_Contract):
    subject_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    target_id: str = Field(pattern=_ID_PATTERN, max_length=80)
    relationship: str = Field(min_length=1, max_length=120)


class TimedEventDeclaration(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    after_turn: int = Field(ge=1, le=100000)
    consequence_facts: tuple[FactDeclaration, ...] = Field(default=(), max_length=16)
    pressure_change: int = Field(ge=-100, le=100, default=0)


class EndingDeclaration(_Contract):
    id: str = Field(pattern=_ID_PATTERN, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    required_fact_ids: tuple[str, ...] = Field(default=(), max_length=32)
    required_beat_ids: tuple[str, ...] = Field(default=(), max_length=32)
    failure_forward: bool = False


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
    scene_purpose: str | None = Field(default=None, max_length=1200)
    dramatic_question: str | None = Field(default=None, max_length=500)
    initial_pressure: int = Field(default=0, ge=0, le=100)
    goals: tuple[GoalDeclaration, ...] = Field(default=(), max_length=32)
    tasks: tuple[TaskDeclaration, ...] = Field(default=(), max_length=64)
    clues: tuple[ClueDeclaration, ...] = Field(default=(), max_length=64)
    relationships: tuple[RelationshipDeclaration, ...] = Field(default=(), max_length=64)
    timed_events: tuple[TimedEventDeclaration, ...] = Field(default=(), max_length=64)
    endings: tuple[EndingDeclaration, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def validate_progression_references(self) -> CompiledStory:
        goal_ids = {goal.id for goal in self.goals}
        if any(task.goal_id not in goal_ids for task in self.tasks):
            raise ValueError("every progression task must reference a declared goal")
        beat_ids = {beat.id for beat in self.beats}
        if any(beat_id not in beat_ids for ending in self.endings for beat_id in ending.required_beat_ids):
            raise ValueError("every ending beat requirement must reference a declared beat")
        event_ids = [event.id for event in self.timed_events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("timed event IDs must be unique")
        return self
