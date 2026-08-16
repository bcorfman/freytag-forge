from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class PredicateDefinitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    arity: int = Field(ge=1)
    arg_types: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    family: Literal[
        "world",
        "perception",
        "knowledge",
        "relationships",
        "tasks",
        "traces",
        "dramatic",
    ] = "world"
    commit_sources: tuple[str, ...] = ("bootstrap", "rule", "intent", "trigger", "system")
    normalization: Literal["trim", "identifier", "literal"] = "trim"
    derived_update_owner: str = "fact_policy"
    proposal_allowed: bool = True


class PredicateSchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    scope: Literal["core", "genre"]
    genre: str = ""
    predicates: tuple[PredicateDefinitionModel, ...]


class RuleConditionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    predicate: str = Field(min_length=1)
    args: tuple[str, ...] = ()


class RuleWhenModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    all: tuple[RuleConditionModel, ...] = ()
    not_conditions: tuple[RuleConditionModel, ...] = Field(default=(), alias="not")


class NumericDeltaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    delta: float


class RuleThenModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assert_facts: tuple[tuple[str, ...], ...] = Field(default=(), alias="assert")
    retract_facts: tuple[tuple[str, ...], ...] = Field(default=(), alias="retract")
    numeric_delta: tuple[NumericDeltaModel, ...] = ()


class RuleModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    when: RuleWhenModel
    then: RuleThenModel
    precedence: int = 0


class RulePackModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    scope: Literal["core", "genre"]
    genre: str = ""
    rules: tuple[RuleModel, ...]


class VoiceCoreIdentityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = ""
    worldview: tuple[str, ...] = ()
    speech_style: tuple[str, ...] = ()
    taboos: tuple[str, ...] = ()
    hard_goals: tuple[str, ...] = ()


class VoiceAdaptiveStateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trust_player: float = 0.5
    fear_level: float = 0.0
    stance_on_player: str = "neutral"
    current_goal: str = ""
    secondary_goals: tuple[str, ...] = ()
    mood_tags: tuple[str, ...] = ()


class VoiceDialogPolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_utterance_sentences: int = Field(ge=1)
    ask_question_bias: float = Field(ge=0.0, le=1.0)
    reveal_thresholds: dict[str, dict[str, float]] = {}


class NPCVoiceCardModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    npc_id: str = Field(min_length=1)
    core_identity: VoiceCoreIdentityModel
    adaptive_state: VoiceAdaptiveStateModel
    dialogue_policy: VoiceDialogPolicyModel


class NPCVoiceCardPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    cards: tuple[NPCVoiceCardModel, ...]


class ActionProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=1)
    targets: tuple[str, ...] = ()
    arguments: dict[str, str] = {}
    disclosed_knowledge: str = ""
    proposed_effects: tuple[str, ...] = ()


class DialogProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speaker: str = Field(min_length=1)
    text: str = Field(min_length=1)
    tone: str = "neutral"


class FactMutationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact: tuple[str, ...] = Field(min_length=2)


class StateUpdateEnvelopeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assert_ops: tuple[FactMutationModel, ...] = Field(default=(), alias="assert")
    retract_ops: tuple[FactMutationModel, ...] = Field(default=(), alias="retract")
    numeric_delta: tuple[NumericDeltaModel, ...] = ()
    reasons: tuple[str, ...] = ()


def _data_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    return payload


def load_predicate_schema(scope_or_genre: str) -> dict[str, Any]:
    key = scope_or_genre.strip().lower()
    if key == "core":
        path = _data_path() / "predicates" / "core.yaml"
    else:
        path = _data_path() / "predicates" / "genres" / f"{key}.yaml"
    model = PredicateSchemaModel.model_validate(_load_yaml(path))
    return model.model_dump(mode="python", by_alias=True)


def load_rule_pack(scope_or_genre: str) -> dict[str, Any]:
    key = scope_or_genre.strip().lower()
    if key == "core":
        path = _data_path() / "rules" / "core_rules.yaml"
    else:
        path = _data_path() / "rules" / "genres" / f"{key}_rules.yaml"
    model = RulePackModel.model_validate(_load_yaml(path))
    return model.model_dump(mode="python", by_alias=True)


def load_policy_bundle(genre: str = "") -> dict[str, Any]:
    """Load and deterministically merge core and optional genre policy data."""
    normalized_genre = genre.strip().lower()
    core = PredicateSchemaModel.model_validate(
        _load_yaml(_data_path() / "predicates" / "core.yaml")
    )
    predicates = list(core.predicates)
    rules = list(
        RulePackModel.model_validate(_load_yaml(_data_path() / "rules" / "core_rules.yaml")).rules
    )
    if normalized_genre:
        predicate_path = _data_path() / "predicates" / "genres" / f"{normalized_genre}.yaml"
        rule_path = _data_path() / "rules" / "genres" / f"{normalized_genre}_rules.yaml"
        if predicate_path.exists():
            predicates.extend(PredicateSchemaModel.model_validate(_load_yaml(predicate_path)).predicates)
        if rule_path.exists():
            rules.extend(RulePackModel.model_validate(_load_yaml(rule_path)).rules)

    predicate_names = [predicate.name for predicate in predicates]
    if len(predicate_names) != len(set(predicate_names)):
        raise ValueError("Policy bundle contains duplicate predicate definitions.")
    rule_ids = [rule.rule_id for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise ValueError("Policy bundle contains duplicate rule identifiers.")

    # A rule's precedence is the only legal tie-breaker. Same-precedence rules
    # with identical conditions and opposite effects are a package error.
    signatures: dict[tuple[object, ...], tuple[tuple[tuple[str, ...], ...], int, str]] = {}
    for rule in rules:
        condition = (
            tuple((item.predicate, item.args) for item in rule.when.all),
            tuple((item.predicate, item.args) for item in rule.when.not_conditions),
        )
        effects = (rule.then.assert_facts, rule.then.retract_facts)
        key = (condition, rule.precedence)
        previous = signatures.get(key)
        if previous is not None and previous[0] != effects:
            raise ValueError(
                f"Conflicting rules '{previous[2]}' and '{rule.rule_id}' at precedence {rule.precedence}."
            )
        signatures[key] = (effects, rule.precedence, rule.rule_id)

    predicates.sort(key=lambda predicate: predicate.name)
    rules.sort(key=lambda rule: (-rule.precedence, rule.rule_id))
    return {
        "schema_version": core.schema_version,
        "genre": normalized_genre,
        "predicates": tuple(predicate.model_dump(mode="python", by_alias=True) for predicate in predicates),
        "rules": tuple(rule.model_dump(mode="python", by_alias=True) for rule in rules),
    }


def load_npc_voice_cards() -> dict[str, Any]:
    path = _data_path() / "npc_voice_cards.yaml"
    model = NPCVoiceCardPayloadModel.model_validate(_load_yaml(path))
    return model.model_dump(mode="python", by_alias=True)


def parse_action_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        model = ActionProposalModel.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Invalid action proposal") from exc
    return model.model_dump(mode="python", by_alias=True)


def parse_dialog_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        model = DialogProposalModel.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Invalid dialog proposal") from exc
    return model.model_dump(mode="python", by_alias=True)


def parse_state_update_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        model = StateUpdateEnvelopeModel.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Invalid state update envelope") from exc
    return model.model_dump(mode="python", by_alias=True)
