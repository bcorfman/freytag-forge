from __future__ import annotations

from typing import Literal, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class BootstrapContractError(ValueError):
    def __init__(self, contract_name: str, detail: str) -> None:
        super().__init__(f"{contract_name}: {detail}")
        self.contract_name = contract_name
        self.detail = detail


class OutlineCastMember(TypedDict):
    name: str
    role: str


class OutlineItem(TypedDict):
    name: str
    kind: str


class StoryOutline(TypedDict):
    premise: str
    setting: str
    tone: str
    cast: tuple[OutlineCastMember, ...]
    items: tuple[OutlineItem, ...]
    main_goal: str
    subgoals: tuple[str, ...]
    event_hints: tuple[str, ...]
    constraints: tuple[str, ...]


class BootstrapLocation(TypedDict):
    id: str
    name: str
    description: str
    exits: dict[str, str]
    traits: tuple[str, ...]


class BootstrapCharacter(TypedDict):
    id: str
    name: str
    description: str
    role: str
    stable_traits: tuple[str, ...]
    dynamic_traits: tuple[str, ...]
    location_id: str
    inventory: tuple[str, ...]


class BootstrapItem(TypedDict):
    id: str
    name: str
    description: str
    kind: str
    stable_traits: tuple[str, ...]
    dynamic_traits: tuple[str, ...]
    location_id: str
    holder_id: str
    portable: bool


class BootstrapGoal(TypedDict):
    goal_id: str
    summary: str
    kind: str
    status: str


class BootstrapFactMutation(TypedDict):
    fact: tuple[str, ...]


class BootstrapNumericDelta(TypedDict):
    key: str
    delta: float


class BootstrapTriggerEffect(TypedDict):
    assert_ops: tuple[BootstrapFactMutation, ...]
    retract_ops: tuple[BootstrapFactMutation, ...]
    numeric_delta: tuple[BootstrapNumericDelta, ...]
    reasons: tuple[str, ...]
    emit_message: str


class BootstrapTrigger(TypedDict):
    trigger_id: str
    kind: str
    enabled: bool
    once: bool
    cooldown_turns: int
    min_turn: int
    action_types: tuple[str, ...]
    actor_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    item_ids: tuple[str, ...]
    location_ids: tuple[str, ...]
    required_facts: tuple[tuple[str, ...], ...]
    forbidden_facts: tuple[tuple[str, ...], ...]
    effects: BootstrapTriggerEffect


class BootstrapPlan(TypedDict):
    outline_id: str
    protagonist_id: str
    locations: tuple[BootstrapLocation, ...]
    characters: tuple[BootstrapCharacter, ...]
    items: tuple[BootstrapItem, ...]
    goals: tuple[BootstrapGoal, ...]
    triggers: tuple[BootstrapTrigger, ...]


class _OutlineCastMemberModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=40)


class _OutlineItemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    kind: str = Field(min_length=1, max_length=40)


class _StoryOutlineModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    premise: str = Field(min_length=1, max_length=280)
    setting: str = Field(min_length=1, max_length=200)
    tone: str = Field(default="neutral", max_length=60)
    cast: tuple[_OutlineCastMemberModel, ...] = Field(default=(), max_length=16)
    items: tuple[_OutlineItemModel, ...] = Field(default=(), max_length=24)
    main_goal: str = Field(min_length=1, max_length=200)
    subgoals: tuple[str, ...] = Field(default=(), max_length=8)
    event_hints: tuple[str, ...] = Field(default=(), max_length=12)
    constraints: tuple[str, ...] = Field(default=(), max_length=12)


class _BootstrapLocationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=300)
    exits: dict[str, str] = Field(default_factory=dict)
    traits: tuple[str, ...] = ()


class _BootstrapCharacterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=220)
    role: str = Field(min_length=1, max_length=40)
    stable_traits: tuple[str, ...] = ()
    dynamic_traits: tuple[str, ...] = ()
    location_id: str = Field(min_length=1, max_length=80)
    inventory: tuple[str, ...] = ()


class _BootstrapItemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=220)
    kind: str = Field(min_length=1, max_length=40)
    stable_traits: tuple[str, ...] = ()
    dynamic_traits: tuple[str, ...] = ()
    location_id: str = Field(default="", max_length=80)
    holder_id: str = Field(default="", max_length=80)
    portable: bool = True


class _BootstrapGoalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_id: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=220)
    kind: str = Field(min_length=1, max_length=40)
    status: Literal["active", "pending", "complete", "failed"] = "pending"


class _BootstrapFactMutationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact: tuple[str, ...] = Field(min_length=2)


class _BootstrapNumericDeltaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=80)
    delta: float


class _BootstrapTriggerEffectModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assert_ops: tuple[_BootstrapFactMutationModel, ...] = Field(default=(), alias="assert")
    retract_ops: tuple[_BootstrapFactMutationModel, ...] = Field(default=(), alias="retract")
    numeric_delta: tuple[_BootstrapNumericDeltaModel, ...] = ()
    reasons: tuple[str, ...] = ()
    emit_message: str = Field(default="", max_length=280)


class _BootstrapTriggerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_id: str = Field(min_length=1, max_length=80)
    kind: Literal["action", "turn"]
    enabled: bool = True
    once: bool = True
    cooldown_turns: int = Field(default=0, ge=0, le=999)
    min_turn: int = Field(default=0, ge=0, le=9999)
    action_types: tuple[str, ...] = ()
    actor_ids: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()
    item_ids: tuple[str, ...] = ()
    location_ids: tuple[str, ...] = ()
    required_facts: tuple[tuple[str, ...], ...] = ()
    forbidden_facts: tuple[tuple[str, ...], ...] = ()
    effects: _BootstrapTriggerEffectModel


class _BootstrapPlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outline_id: str = Field(min_length=1, max_length=80)
    protagonist_id: str = Field(min_length=1, max_length=80)
    locations: tuple[_BootstrapLocationModel, ...] = Field(min_length=1, max_length=32)
    characters: tuple[_BootstrapCharacterModel, ...] = Field(min_length=1, max_length=32)
    items: tuple[_BootstrapItemModel, ...] = Field(default=(), max_length=64)
    goals: tuple[_BootstrapGoalModel, ...] = Field(default=(), max_length=16)
    triggers: tuple[_BootstrapTriggerModel, ...] = Field(default=(), max_length=64)


def _raise_contract_error(contract_name: str, exc: ValidationError) -> BootstrapContractError:
    error = exc.errors()[0]
    location = ".".join(str(part) for part in error["loc"])
    return BootstrapContractError(contract_name, f"{location}:{error['type']}")


def parse_story_outline(payload: dict[str, object]) -> StoryOutline:
    try:
        model = _StoryOutlineModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("StoryOutline", exc) from exc
    return cast(StoryOutline, model.model_dump(mode="python"))


def parse_bootstrap_plan(payload: dict[str, object]) -> BootstrapPlan:
    try:
        model = _BootstrapPlanModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("BootstrapPlan", exc) from exc
    return cast(BootstrapPlan, model.model_dump(mode="python", by_alias=True))
