from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CRITIQUE_DIMENSIONS = ("continuity", "causality", "dialogue_fit")
MAX_RATIONALE_CHARS = 280
MAX_FEEDBACK_CHARS = 280
MAX_INSTRUCTION_CHARS = 320
MAX_NARRATION_CHARS = 3000
MAX_PATCH_OPERATIONS = 24
MAX_DIALOGUE_LINES = 8


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


class FactMutation(TypedDict):
    fact: tuple[str, ...]


class NumericDelta(TypedDict):
    key: str
    delta: float


class StateDeltaProposal(TypedDict):
    assert_ops: tuple[FactMutation, ...]
    retract_ops: tuple[FactMutation, ...]
    numeric_delta: tuple[NumericDelta, ...]
    reasons: tuple[str, ...]


class SemanticActionProposal(TypedDict):
    action_id: str
    action_type: str
    actor_id: str
    target_id: str
    item_id: str
    location_id: str


class PlayerIntentProposal(TypedDict):
    summary: str
    addressed_npc_id: str
    target_ids: tuple[str, ...]
    item_ids: tuple[str, ...]
    location_id: str


class SceneFramingProposal(TypedDict):
    focus: str
    dramatic_question: str
    player_approach: str


class NpcDialogueProposal(TypedDict):
    speaker_id: str
    text: str


class BeatHintsProposal(TypedDict):
    escalation: str
    reveal_thread_ids: tuple[str, ...]
    obstacle_mode: str


class TurnProposal(TypedDict):
    turn_id: str
    mode: str
    player_intent: PlayerIntentProposal
    scene_framing: SceneFramingProposal
    npc_dialogue: NpcDialogueProposal
    narration: str
    semantic_actions: tuple[SemanticActionProposal, ...]
    state_delta: StateDeltaProposal
    beat_hints: BeatHintsProposal


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
    narration: str = Field(default="", max_length=MAX_NARRATION_CHARS)
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


class _FactMutationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact: tuple[str, ...] = Field(min_length=2)


class _NumericDeltaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=80)
    delta: float


class _StateDeltaProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assert_ops: tuple[_FactMutationModel, ...] = Field(default=(), alias="assert")
    retract_ops: tuple[_FactMutationModel, ...] = Field(default=(), alias="retract")
    numeric_delta: tuple[_NumericDeltaModel, ...] = ()
    reasons: tuple[str, ...] = ()


class _SemanticActionProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, max_length=80)
    action_type: str = Field(min_length=1, max_length=40)
    actor_id: str = Field(default="player", min_length=1, max_length=80)
    target_id: str = Field(default="", max_length=80)
    item_id: str = Field(default="", max_length=80)
    location_id: str = Field(default="", max_length=80)


class _PlayerIntentProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=160)
    addressed_npc_id: str = Field(default="", max_length=80)
    target_ids: tuple[str, ...] = Field(default=(), max_length=8)
    item_ids: tuple[str, ...] = Field(default=(), max_length=8)
    location_id: str = Field(default="", max_length=80)


class _SceneFramingProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus: str = Field(default="", max_length=160)
    dramatic_question: str = Field(default="", max_length=240)
    player_approach: str = Field(default="", max_length=80)


class _NpcDialogueProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speaker_id: str = Field(default="", max_length=80)
    text: str = Field(default="", max_length=MAX_NARRATION_CHARS)


class _BeatHintsProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    escalation: Literal["none", "soft", "hard"] = "none"
    reveal_thread_ids: tuple[str, ...] = Field(default=(), max_length=8)
    obstacle_mode: str = Field(default="", max_length=80)


class _TurnProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(min_length=1, max_length=80)
    mode: Literal["scene", "conversation", "physical", "social", "investigation"] = "scene"
    player_intent: _PlayerIntentProposalModel
    scene_framing: _SceneFramingProposalModel = _SceneFramingProposalModel()
    npc_dialogue: _NpcDialogueProposalModel = _NpcDialogueProposalModel()
    narration: str = Field(default="", max_length=MAX_NARRATION_CHARS)
    semantic_actions: tuple[_SemanticActionProposalModel, ...] = Field(default=(), max_length=12)
    state_delta: _StateDeltaProposalModel
    beat_hints: _BeatHintsProposalModel = _BeatHintsProposalModel()

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_turn_shape(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        if "player_intent" in payload or "mode" in payload:
            return payload
        legacy_intent = str(payload.get("intent", "")).strip()
        if not legacy_intent:
            return payload
        semantic_actions = payload.get("semantic_actions", ())
        target_ids: list[str] = []
        item_ids: list[str] = []
        location_id = ""
        if isinstance(semantic_actions, (list, tuple)):
            for action in semantic_actions:
                if not isinstance(action, dict):
                    continue
                target_id = str(action.get("target_id", "")).strip()
                item_id = str(action.get("item_id", "")).strip()
                action_location_id = str(action.get("location_id", "")).strip()
                if target_id:
                    target_ids.append(target_id)
                if item_id:
                    item_ids.append(item_id)
                if action_location_id and not location_id:
                    location_id = action_location_id
        speaker_id, dialogue_text = _legacy_dialogue_line_to_npc_dialogue(payload.get("dialogue_lines", ()))
        return {
            "turn_id": payload.get("turn_id", ""),
            "mode": _mode_from_legacy_intent(legacy_intent),
            "player_intent": {
                "summary": legacy_intent,
                "addressed_npc_id": target_ids[0] if target_ids else "",
                "target_ids": target_ids,
                "item_ids": item_ids,
                "location_id": location_id,
            },
            "scene_framing": {
                "focus": "",
                "dramatic_question": "",
                "player_approach": "",
            },
            "semantic_actions": semantic_actions,
            "state_delta": payload.get("state_delta", {}),
            "npc_dialogue": {
                "speaker_id": speaker_id,
                "text": dialogue_text,
            },
            "narration": payload.get("narration", ""),
            "beat_hints": {
                "escalation": "none",
                "reveal_thread_ids": (),
                "obstacle_mode": "",
            },
        }


def _build_validation_error(
    code: str,
    contract_name: str,
    exc: ValidationError,
) -> ContractValidationError:
    first = exc.errors()[0]
    location = ".".join(str(chunk) for chunk in first["loc"])
    detail = f"{location}:{first['type']}"
    return ContractValidationError(code=code, contract_name=contract_name, detail=detail)


def _mode_from_legacy_intent(intent: str) -> str:
    normalized = intent.strip().lower()
    if normalized in {"ask_about", "greet", "apologize", "threaten", "question", "query"}:
        return "conversation"
    if normalized in {"take", "take_item", "move", "move_to", "use"}:
        return "physical"
    if normalized in {"inspect", "inspect_item", "read_case_file", "read_ledger_page", "search"}:
        return "investigation"
    return "scene"


def _legacy_dialogue_line_to_npc_dialogue(value: Any) -> tuple[str, str]:
    if not isinstance(value, (list, tuple)) or not value:
        return "", ""
    first_line = str(value[0]).strip()
    if not first_line:
        return "", ""
    match = re.match(r'^(?P<speaker>[^"]+?) says: "(?P<text>.*)"$', first_line)
    if match is None:
        return "", ""
    speaker = match.group("speaker").strip()
    text = match.group("text").strip()
    normalized_speaker = speaker.lower().replace(" ", "_")
    return normalized_speaker, text


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


def parse_turn_proposal(payload: dict[str, Any]) -> TurnProposal:
    try:
        model = _TurnProposalModel.model_validate(payload)
    except ValidationError as exc:
        raise _build_validation_error("CONTRACT_INVALID_TURN_PROPOSAL", "TurnProposal", exc) from exc
    return cast(TurnProposal, model.model_dump(mode="python", by_alias=True))


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
