from __future__ import annotations

import hashlib
import json
from typing import Literal, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CRITIQUE_DIMENSIONS = ("continuity", "causality", "dialogue_fit")
MAX_RATIONALE_CHARS = 280
MAX_FEEDBACK_CHARS = 280
MAX_INSTRUCTION_CHARS = 320
MAX_NARRATION_CHARS = 3000
MAX_PATCH_OPERATIONS = 24


class ContractValidationError(ValueError):
    def __init__(self, code: str, contract_name: str, detail: str) -> None:
        super().__init__(f"{code}: {contract_name}: {detail}")
        self.code = code
        self.contract_name = contract_name
        self.detail = detail


class ScoreVector(TypedDict):
    continuity: int
    causality: int
    dialogue_fit: int


class CriticalFloors(TypedDict):
    continuity: int
    causality: int


class PatchOperation(TypedDict):
    op: str
    path: str
    value: str


class StoryPatch(TypedDict):
    patch_id: str
    operations: tuple[PatchOperation, ...]
    rationale: str


class AgentProposal(TypedDict):
    agent_id: str
    narration: str
    story_patch: StoryPatch
    rationale: str


class CritiqueReport(TypedDict):
    critic_id: str
    scores: ScoreVector
    feedback: str


class JudgeDecision(TypedDict):
    decision_id: str
    status: str
    round_index: int
    threshold: int
    total_score: int
    rubric_components: ScoreVector
    critical_floors: CriticalFloors
    critic_ids: tuple[str, ...]
    critic_reports: tuple[CritiqueReport, ...]
    judge: str
    rationale: str


class RevisionDirective(TypedDict):
    directive_id: str
    target_agent_id: str
    focus_dimensions: tuple[str, ...]
    instruction: str
    rationale: str


class _ScoreVectorModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continuity: int = Field(ge=0, le=100)
    causality: int = Field(ge=0, le=100)
    dialogue_fit: int = Field(ge=0, le=100)


class _CriticalFloorsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continuity: int = Field(ge=0, le=100)
    causality: int = Field(ge=0, le=100)


class _PatchOperationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["set", "add", "remove"]
    path: str = Field(min_length=1, max_length=160)
    value: str = Field(max_length=MAX_NARRATION_CHARS)


class _StoryPatchModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patch_id: str = Field(min_length=1, max_length=80)
    operations: tuple[_PatchOperationModel, ...] = Field(max_length=MAX_PATCH_OPERATIONS)
    rationale: str = Field(min_length=1, max_length=MAX_RATIONALE_CHARS)


class _AgentProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=80)
    narration: str = Field(min_length=1, max_length=MAX_NARRATION_CHARS)
    story_patch: _StoryPatchModel
    rationale: str = Field(min_length=1, max_length=MAX_RATIONALE_CHARS)


class _CritiqueReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critic_id: str = Field(min_length=1, max_length=80)
    scores: _ScoreVectorModel
    feedback: str = Field(min_length=1, max_length=MAX_FEEDBACK_CHARS)


class _JudgeDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1, max_length=96)
    status: Literal["accepted", "failed"]
    round_index: int = Field(ge=0, le=100)
    threshold: int = Field(ge=0, le=100)
    total_score: int = Field(ge=0, le=100)
    rubric_components: _ScoreVectorModel
    critical_floors: _CriticalFloorsModel
    critic_ids: tuple[str, ...] = Field(max_length=16)
    critic_reports: tuple[_CritiqueReportModel, ...] = Field(max_length=16)
    judge: str = Field(min_length=1, max_length=80)
    rationale: str = Field(min_length=1, max_length=MAX_RATIONALE_CHARS)

    @model_validator(mode="after")
    def _validate_critic_references(self) -> _JudgeDecisionModel:
        report_ids = tuple(report.critic_id for report in self.critic_reports)
        if self.critic_ids != report_ids:
            raise ValueError("critic_ids must match critic_reports order.")
        return self


class _RevisionDirectiveModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    directive_id: str = Field(min_length=1, max_length=96)
    target_agent_id: str = Field(min_length=1, max_length=80)
    focus_dimensions: tuple[Literal["continuity", "causality", "dialogue_fit"], ...] = Field(
        min_length=1,
        max_length=3,
    )
    instruction: str = Field(min_length=1, max_length=MAX_INSTRUCTION_CHARS)
    rationale: str = Field(min_length=1, max_length=MAX_RATIONALE_CHARS)


def _build_validation_error(
    code: str,
    contract_name: str,
    exc: ValidationError,
) -> ContractValidationError:
    first = exc.errors()[0]
    location = ".".join(str(chunk) for chunk in first["loc"])
    detail = f"{location}:{first['type']}"
    return ContractValidationError(code=code, contract_name=contract_name, detail=detail)


def parse_story_patch(payload: dict[str, object]) -> StoryPatch:
    try:
        model = _StoryPatchModel.model_validate(payload)
    except ValidationError as exc:
        raise _build_validation_error("CONTRACT_INVALID_STORY_PATCH", "StoryPatch", exc) from exc
    return cast(StoryPatch, model.model_dump(mode="python"))


def parse_agent_proposal(payload: dict[str, object]) -> AgentProposal:
    try:
        model = _AgentProposalModel.model_validate(payload)
    except ValidationError as exc:
        raise _build_validation_error("CONTRACT_INVALID_AGENT_PROPOSAL", "AgentProposal", exc) from exc
    return cast(AgentProposal, model.model_dump(mode="python"))


def parse_critique_report(payload: dict[str, object]) -> CritiqueReport:
    try:
        model = _CritiqueReportModel.model_validate(payload)
    except ValidationError as exc:
        raise _build_validation_error("CONTRACT_INVALID_CRITIQUE_REPORT", "CritiqueReport", exc) from exc
    return cast(CritiqueReport, model.model_dump(mode="python"))


def parse_judge_decision(payload: dict[str, object]) -> JudgeDecision:
    try:
        model = _JudgeDecisionModel.model_validate(payload)
    except ValidationError as exc:
        raise _build_validation_error("CONTRACT_INVALID_JUDGE_DECISION", "JudgeDecision", exc) from exc
    return cast(JudgeDecision, model.model_dump(mode="python"))


def parse_revision_directive(payload: dict[str, object]) -> RevisionDirective:
    try:
        model = _RevisionDirectiveModel.model_validate(payload)
    except ValidationError as exc:
        raise _build_validation_error("CONTRACT_INVALID_REVISION_DIRECTIVE", "RevisionDirective", exc) from exc
    return cast(RevisionDirective, model.model_dump(mode="python"))


def narration_to_agent_proposal(agent_id: str, narration: str) -> AgentProposal:
    digest_payload = {"agent_id": agent_id, "narration": narration}
    digest = hashlib.sha256(json.dumps(digest_payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return parse_agent_proposal(
        {
            "agent_id": agent_id,
            "narration": narration,
            "story_patch": {
                "patch_id": f"patch-{digest}",
                "operations": (),
                "rationale": "Narration-only proposal.",
            },
            "rationale": "Narration generated for coherence validation.",
        }
    )
