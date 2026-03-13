from __future__ import annotations

from typing import TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class StoryAgentContractError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class CharacterContact(TypedDict):
    name: str
    role: str
    trait: str


class StoryArchitectOutput(TypedDict):
    protagonist_name: str
    protagonist_background: str
    secrets_to_hide: list[str]
    tone: str


class CharacterDesignerOutput(TypedDict):
    contacts: list[CharacterContact]


class PlotDesignerOutput(TypedDict):
    assistant_name: str
    actionable_objective: str


class NarratorOpeningOutput(TypedDict):
    paragraphs: list[str]


class _StoryArchitectModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protagonist_name: str = Field(min_length=1, max_length=80)
    protagonist_background: str = Field(min_length=1, max_length=500)
    secrets_to_hide: list[str] = Field(default_factory=list, max_length=8)
    tone: str = Field(min_length=1, max_length=40)


class _CharacterContactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=60)
    trait: str = Field(min_length=1, max_length=60)


class _CharacterDesignerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contacts: list[_CharacterContactModel] = Field(min_length=1, max_length=8)


class _PlotDesignerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assistant_name: str = Field(min_length=1, max_length=80)
    actionable_objective: str = Field(min_length=1, max_length=300)


class _NarratorOpeningModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraphs: list[str] = Field(min_length=3, max_length=4)


def _raise_contract_error(code: str, exc: ValidationError) -> StoryAgentContractError:
    first = exc.errors()[0]
    location = ".".join(str(chunk) for chunk in first["loc"])
    return StoryAgentContractError(code, f"{location}:{first['type']}")


def parse_story_architect_output(payload: dict) -> StoryArchitectOutput:
    try:
        model = _StoryArchitectModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("STORY_ARCHITECT_CONTRACT_INVALID", exc) from exc
    return cast(StoryArchitectOutput, model.model_dump(mode="python"))


def parse_character_designer_output(payload: dict) -> CharacterDesignerOutput:
    try:
        model = _CharacterDesignerModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("CHARACTER_DESIGNER_CONTRACT_INVALID", exc) from exc
    contacts = model.model_dump(mode="python")["contacts"]
    invalid_placeholder = {"premise", "scene", "outline", "characters"}
    for contact in contacts:
        if contact["name"].strip().lower() in invalid_placeholder:
            raise StoryAgentContractError("CHARACTER_DESIGNER_CONTRACT_INVALID", "contacts.name:placeholder_label")
    return cast(CharacterDesignerOutput, {"contacts": contacts})


def parse_plot_designer_output(payload: dict) -> PlotDesignerOutput:
    try:
        model = _PlotDesignerModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("PLOT_DESIGNER_CONTRACT_INVALID", exc) from exc
    return cast(PlotDesignerOutput, model.model_dump(mode="python"))


def parse_narrator_opening_output(payload: dict) -> NarratorOpeningOutput:
    try:
        model = _NarratorOpeningModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("NARRATOR_OPENING_CONTRACT_INVALID", exc) from exc
    paragraphs = [paragraph.strip() for paragraph in model.paragraphs if paragraph.strip()]
    if len(paragraphs) < 3:
        raise StoryAgentContractError("NARRATOR_OPENING_CONTRACT_INVALID", "paragraphs:min_length")
    return cast(NarratorOpeningOutput, {"paragraphs": paragraphs[:4]})
