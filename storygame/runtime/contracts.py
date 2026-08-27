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
    # Structured segments are primary. ``narration`` is a derived compatibility
    # field for older runtime consumers and API ``lines``.
    narration: str = Field(default="", max_length=12000)
    segments: tuple[NarrationSegment, ...] = ()
    narrative_seconds: int = Field(default=60, ge=40, le=80)
    operations: tuple[FactOperation, ...] = ()
    transition: SceneTransitionProposal | None = None
    events: tuple[StoryEventProposal, ...] = ()
    game_break: GameBreakWarning | None = None

    @model_validator(mode="after")
    def no_duplicate_events(self) -> TurnProposal:
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("event IDs must be unique")
        if self.narration:
            return self
        narration = " ".join(segment.text for segment in self.segments)
        if not narration:
            raise ValueError("a turn proposal needs narration or structured segments")
        if len(narration) > 12000:
            raise ValueError("derived narration is too long")
        return self.model_copy(update={"narration": narration})


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
