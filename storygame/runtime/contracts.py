"""Strict, provider-neutral proposals accepted by the scene runtime."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from storygame.runtime.facts import Fact


class RuntimeContractError(ValueError):
    """Raised when an untrusted provider envelope cannot become a proposal."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FactOperation(_StrictModel):
    operation: Literal["assert", "retract"]
    fact: Fact


class SceneTransitionProposal(_StrictModel):
    transition_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class StoryEventProposal(_StrictModel):
    event_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    realization_id: str | None = Field(default=None, min_length=1)
    knowledge_ids: tuple[str, ...] = ()
    operations: tuple[FactOperation, ...] = ()


class GameBreakWarning(_StrictModel):
    """A persistent, explicit decision before accepting a risky candidate."""

    warning_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    reason: str = Field(min_length=1, max_length=1200)
    affected_ids: tuple[str, ...] = ()
    snapshot_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class NarrationSegment(_StrictModel):
    """A provider-authored block with stable grounding for later validation."""

    kind: Literal["narration", "dialogue", "action"]
    text: str = Field(min_length=1, max_length=12000)
    speaker_id: str | None = None
    grounding_ids: tuple[str, ...] = ()


class TurnProposal(_StrictModel):
    """The complete untrusted normal-turn provider contract.

    A provider may narrate and select one authored knowledge unit.  It cannot
    name package routes, mutate facts, or choose a transition.
    """

    segments: tuple[NarrationSegment, ...] = Field(min_length=1)
    selected_knowledge_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def has_unique_selections(self) -> TurnProposal:
        if len(set(self.selected_knowledge_ids)) != len(self.selected_knowledge_ids):
            raise ValueError("selected knowledge IDs must be unique")
        return self

    @property
    def narration(self) -> str:
        return " ".join(segment.text for segment in self.segments)


class ResolvedTurnProposal(_StrictModel):
    """Internal, package-derived candidate accepted by the state boundary."""

    segments: tuple[NarrationSegment, ...] = Field(min_length=1)
    selected_knowledge_ids: tuple[str, ...] = ()
    narrative_seconds: int = Field(default=60, ge=40, le=80)
    operations: tuple[FactOperation, ...] = ()
    transition: SceneTransitionProposal | None = None
    events: tuple[StoryEventProposal, ...] = ()
    game_break: GameBreakWarning | None = None

    @model_validator(mode="after")
    def no_duplicate_events(self) -> ResolvedTurnProposal:
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("event IDs must be unique")
        return self

    @property
    def narration(self) -> str:
        return " ".join(segment.text for segment in self.segments)


def parse_turn_proposal(envelope: object) -> TurnProposal:
    """Normalize common provider wrappers, then fail closed on invalid JSON/schema."""

    payload: object = envelope
    if isinstance(payload, dict) and "response" in payload:
        payload = payload["response"]
    if isinstance(payload, dict) and "content" in payload:
        payload = payload["content"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as error:
            raise RuntimeContractError("provider response is not JSON") from error
    try:
        return TurnProposal.model_validate(payload)
    except ValidationError as error:
        raise RuntimeContractError("provider response violates the turn contract") from error


def contract_error_summary(error: RuntimeContractError) -> str:
    """Return safe validation paths/types without returning untrusted provider values."""

    cause = error.__cause__
    if not isinstance(cause, ValidationError):
        return "invalid JSON" if isinstance(cause, json.JSONDecodeError) else ""
    return ", ".join(f"{'.'.join(str(part) for part in issue['loc'])}:{issue['type']}" for issue in cause.errors())
