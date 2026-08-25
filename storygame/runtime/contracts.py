"""Untrusted provider output contracts for the minimal V2 runtime."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class RuntimeFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class StateOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["set", "add", "remove"]
    path: str = Field(min_length=1, max_length=160)
    value: Any


class BeatUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    beat_id: str = Field(min_length=1, max_length=80)
    route_id: str | None = Field(default=None, min_length=1, max_length=80)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=32)
    route_failed: bool = False
    completion_tags: tuple[str, ...] = Field(default=(), max_length=16)
    evidence: str = Field(default="", max_length=800)


class StoryletRealization(BaseModel):
    """A bounded claim to realize one eligible reviewed storylet."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    storylet_id: str = Field(min_length=1, max_length=80)
    realization_mode: str = Field(min_length=1, max_length=80)
    consequence_ids: tuple[str, ...] = Field(default=(), max_length=16)
    completion_evidence: tuple[str, ...] = Field(default=(), max_length=16)
    abort_evidence: tuple[str, ...] = Field(default=(), max_length=16)


class SpeechSegment(BaseModel):
    """One attributed utterance in a proposed interaction."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["speech"] = "speech"
    speaker_id: str = Field(min_length=1, max_length=80)
    addressee_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    used_fact_ids: tuple[str, ...] = Field(default=(), max_length=32)
    text: str = Field(min_length=1, max_length=2000)


class ActionSegment(BaseModel):
    """A transient expression or a fact-backed visible material action."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["action"] = "action"
    actor_id: str = Field(min_length=1, max_length=80)
    grounding: Literal["expressive", "material"]
    text: str = Field(min_length=1, max_length=2000)
    effect_refs: tuple[str, ...] = Field(default=(), max_length=16)


class InteractionEffect(BaseModel):
    """A named bounded operation that can ground a material action segment."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=1, max_length=80)
    operation: StateOperation


class InteractionProposal(BaseModel):
    """An ordered, frame-bound interaction accepted only as one atomic decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    interaction_frame_id: str = Field(min_length=1, max_length=80)
    initiation: Literal["npc_initiated", "player_initiated", "continuation"]
    participant_ids: tuple[str, ...] = Field(min_length=2, max_length=16)
    segments: tuple[SpeechSegment | ActionSegment, ...] = Field(min_length=1, max_length=32)
    effects: tuple[InteractionEffect, ...] = Field(default=(), max_length=16)
    storylet_realization: StoryletRealization | None = None
    agency_mode: Literal["engage", "refuse", "redirect", "interrupt", "depart"] | None = None
    outcome: Literal["continue", "complete", "abort"] = "continue"

    @model_validator(mode="after")
    def _validate_effect_references(self) -> InteractionProposal:
        effect_ids = [effect.id for effect in self.effects]
        if len(effect_ids) != len(set(effect_ids)):
            raise ValueError("interaction effect IDs must be unique")
        known_effects = set(effect_ids)
        for segment in self.segments:
            if isinstance(segment, ActionSegment):
                if segment.grounding == "expressive" and segment.effect_refs:
                    raise ValueError("expressive action segments cannot reference durable effects")
                if segment.grounding == "material" and not segment.effect_refs:
                    raise ValueError("material action segments require effect references")
                if not set(segment.effect_refs) <= known_effects:
                    raise ValueError("action segment references an unknown interaction effect")
        return self


class DialogueProposal(BaseModel):
    """A validated addressed-NPC response with bounded state effects."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    target_id: str = Field(min_length=1, max_length=80)
    speaker_id: str = Field(min_length=1, max_length=80)
    permitted_context: tuple[str, ...] = Field(default=(), max_length=32)
    dialogue: str = Field(min_length=1, max_length=2000)
    effects: tuple[StateOperation, ...] = Field(default=(), max_length=16)


class DocumentDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    item_id: str = Field(min_length=1, max_length=80)
    speaker_id: str = Field(min_length=1, max_length=80)
    fact_id: str = Field(min_length=1, max_length=120)


class TurnResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    narration: str = Field(min_length=1, max_length=4000)
    operations: tuple[StateOperation, ...] = Field(default=(), max_length=32)
    beat_updates: tuple[BeatUpdate, ...] = Field(default=(), max_length=16)
    disclosures: tuple[DocumentDisclosure, ...] = Field(default=(), max_length=16)
    interaction: InteractionProposal | None = None
    dialogue: DialogueProposal | None = None
    storylet_realization: StoryletRealization | None = None
    summary_delta: str | None = Field(default=None, max_length=1200)
    material_progress: bool = False

    @model_validator(mode="after")
    def _single_response_authority(self) -> TurnResult:
        if self.interaction is not None and self.dialogue is not None:
            raise ValueError("a turn cannot contain both interaction and dialogue proposals")
        if self.interaction is not None and self.storylet_realization is not None:
            raise ValueError("interaction storylet realization must be nested in the interaction proposal")
        return self

    @classmethod
    def from_provider(cls, response: object) -> TurnResult:
        try:
            return cls.model_validate(_json_payload(response))
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeFailure("INVALID_TURN", f"provider response failed local turn validation: {exc}") from exc


def _json_payload(response: object) -> object:
    value = _unwrap(response)
    if isinstance(value, str):
        fenced = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", value, re.DOTALL | re.IGNORECASE)
        value = fenced.group(1) if fenced else value
        return json.loads(value)
    if isinstance(value, (dict, list)):
        return value
    raise ValueError("provider response has no JSON-compatible content")


def _unwrap(value: object) -> object:
    if not isinstance(value, dict):
        return value
    if "result" in value and isinstance(value["result"], dict):
        return _unwrap(value["result"].get("response", value["result"]))
    if "response" in value:
        return _unwrap(value["response"])
    choices = value.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict) and "content" in message:
            return _unwrap(message["content"])
    message = value.get("message")
    if isinstance(message, dict) and "content" in message:
        return _unwrap(message["content"])
    return value
