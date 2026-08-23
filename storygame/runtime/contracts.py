"""Untrusted provider output contracts for the minimal V2 runtime."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


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
    dialogue: DialogueProposal | None = None
    summary_delta: str | None = Field(default=None, max_length=1200)
    material_progress: bool = False

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
