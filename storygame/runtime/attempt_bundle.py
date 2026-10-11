"""Versioned, typed observation of one runtime turn attempt."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _BundleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AttemptIdentity(_BundleModel):
    code_sha: str | None = None
    package_id: str | None = None
    package_version: str | None = None
    package_content_hash: str | None = None
    semantic_fallback: bool | None = None
    projection_cap: int | None = None


class AttemptPreState(_BundleModel):
    scene_id: str
    turn_index: int
    turns_since_scene_entry: int
    staged_cue_fact_id: str | None = None
    staged_handoff_fact_ids: tuple[str, ...] = ()
    delivered_cue_ids: tuple[str, ...] = ()
    fact_predicates: tuple[str, ...] = ()


class AttemptCommand(_BundleModel):
    raw: str
    normalized: str


class ModelStage(_BundleModel):
    kind: Literal["narration", "semantic_match", "capture"]
    request: str | dict[str, Any] | None = None
    reply: str | dict[str, Any] | list[Any] | None = None
    error: str | None = None


class SelectedReveal(_BundleModel):
    knowledge_ids: tuple[str, ...] = ()
    delivery_fact_ids: tuple[str, ...] = ()


class RevealSelection(_BundleModel):
    outcome: str
    matched: str | None = None
    universe_size: int = 0
    shortlist_size: int = 0


class ContractShadow(_BundleModel):
    ran: bool = False
    answers: dict[str, bool | None] = Field(default_factory=dict)
    granted: str | None = None
    ambiguous: bool = False
    live_matched: str | None = None
    agrees: bool = False
    skipped: str | None = None


class CommittedDelta(_BundleModel):
    fact_predicates: tuple[str, ...] = ()
    scene_from: str | None = None
    scene_to: str | None = None


class CueStage(_BundleModel):
    fact_id: str | None = None
    delivered: bool = False
    consumed: bool = False


class AttemptError(_BundleModel):
    code: str | None = None
    message: str


class AttemptBundle(_BundleModel):
    """The complete observation of one attempt, including rejected attempts."""

    schema_version: int = Field(default=1, strict=True)
    identity: AttemptIdentity
    pre_state: AttemptPreState
    command: AttemptCommand
    stages: tuple[ModelStage, ...] = ()
    selected_reveal: SelectedReveal = SelectedReveal()
    reveal_selection: RevealSelection | None = None
    contract_shadow: ContractShadow | None = None
    committed_delta: CommittedDelta = CommittedDelta()
    cue_stage: CueStage = CueStage()
    transition_cause: Literal["none", "earned", "forced", "timer"] = "none"
    outcome: Literal["committed", "rejected", "game_break", "operational_failure"]
    rejection: AttemptError | None = None
    operational_failure: AttemptError | None = None

    @model_validator(mode="after")
    def supported_version(self) -> AttemptBundle:
        if self.schema_version != 1:
            raise ValueError(f"unsupported attempt bundle schema version: {self.schema_version}")
        return self

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, value: str) -> AttemptBundle:
        return cls.model_validate_json(value)
