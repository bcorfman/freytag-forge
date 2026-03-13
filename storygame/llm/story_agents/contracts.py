from __future__ import annotations

import re
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
    model_config = ConfigDict(extra="ignore")

    protagonist_name: str = Field(min_length=1, max_length=80)
    protagonist_background: str = Field(min_length=1, max_length=500)
    secrets_to_hide: list[str] = Field(default_factory=list, max_length=8)
    tone: str = Field(min_length=1, max_length=40)


class _CharacterContactModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=60)
    trait: str = Field(min_length=1, max_length=60)


class _CharacterDesignerModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contacts: list[_CharacterContactModel] = Field(min_length=1, max_length=8)


class _PlotDesignerModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assistant_name: str = Field(min_length=1, max_length=80)
    actionable_objective: str = Field(min_length=1, max_length=300)


class _NarratorOpeningModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    paragraphs: list[str] = Field(min_length=3, max_length=4)


def _raise_contract_error(code: str, exc: ValidationError) -> StoryAgentContractError:
    first = exc.errors()[0]
    location = ".".join(str(chunk) for chunk in first["loc"])
    return StoryAgentContractError(code, f"{location}:{first['type']}")


def _trim_sentence(text: str) -> str:
    cleaned = " ".join(text.split()).strip(" ,")
    if not cleaned:
        return ""
    return cleaned


def _strip_label(value: str, labels: tuple[str, ...]) -> str:
    cleaned = _trim_sentence(value)
    for label in labels:
        prefix = f"{label}:"
        if cleaned.lower().startswith(prefix):
            return cleaned[len(prefix) :].strip()
    return cleaned


def _ensure_terminal_punctuation(text: str) -> str:
    cleaned = _trim_sentence(text)
    if not cleaned:
        return ""
    if cleaned[-1] in ".!?":
        return cleaned
    return f"{cleaned}."


def _is_placeholder_contact_name(name: str) -> bool:
    return re.fullmatch(r"(premise|scene|outline|characters)\s*:?", name.strip().lower()) is not None


def parse_story_architect_output(payload: dict) -> StoryArchitectOutput:
    try:
        model = _StoryArchitectModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("STORY_ARCHITECT_CONTRACT_INVALID", exc) from exc
    parsed = model.model_dump(mode="python")
    normalized = {
        "protagonist_name": _strip_label(str(parsed["protagonist_name"]), ("name", "protagonist")),
        "protagonist_background": _ensure_terminal_punctuation(
            _strip_label(str(parsed["protagonist_background"]), ("background", "history"))
        ),
        "secrets_to_hide": [_trim_sentence(str(secret)) for secret in parsed["secrets_to_hide"] if _trim_sentence(str(secret))],
        "tone": _trim_sentence(str(parsed["tone"])).lower(),
    }
    if not normalized["protagonist_name"]:
        raise StoryAgentContractError("STORY_ARCHITECT_CONTRACT_INVALID", "protagonist_name:min_length")
    if not normalized["protagonist_background"]:
        raise StoryAgentContractError("STORY_ARCHITECT_CONTRACT_INVALID", "protagonist_background:min_length")
    return cast(StoryArchitectOutput, normalized)


def parse_character_designer_output(payload: dict) -> CharacterDesignerOutput:
    try:
        model = _CharacterDesignerModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("CHARACTER_DESIGNER_CONTRACT_INVALID", exc) from exc
    contacts = model.model_dump(mode="python")["contacts"]
    normalized_contacts: list[CharacterContact] = []
    for contact in contacts:
        name = _strip_label(str(contact["name"]), ("name", "character"))
        role = _strip_label(str(contact["role"]), ("role",))
        trait = _strip_label(str(contact["trait"]), ("trait", "tone"))
        if _is_placeholder_contact_name(name):
            continue
        if not name or not role or not trait:
            continue
        normalized_contacts.append({"name": name, "role": role, "trait": trait})
    if not normalized_contacts:
        raise StoryAgentContractError("CHARACTER_DESIGNER_CONTRACT_INVALID", "contacts:missing_valid_contact")
    return cast(CharacterDesignerOutput, {"contacts": normalized_contacts})


def parse_plot_designer_output(payload: dict) -> PlotDesignerOutput:
    try:
        model = _PlotDesignerModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("PLOT_DESIGNER_CONTRACT_INVALID", exc) from exc
    parsed = model.model_dump(mode="python")
    normalized = {
        "assistant_name": _strip_label(str(parsed["assistant_name"]), ("assistant_name", "assistant", "name")),
        "actionable_objective": _ensure_terminal_punctuation(
            _strip_label(str(parsed["actionable_objective"]), ("actionable_objective", "objective"))
        ),
    }
    if not normalized["assistant_name"]:
        raise StoryAgentContractError("PLOT_DESIGNER_CONTRACT_INVALID", "assistant_name:min_length")
    if not normalized["actionable_objective"]:
        raise StoryAgentContractError("PLOT_DESIGNER_CONTRACT_INVALID", "actionable_objective:min_length")
    return cast(PlotDesignerOutput, normalized)


def parse_narrator_opening_output(payload: dict) -> NarratorOpeningOutput:
    try:
        model = _NarratorOpeningModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("NARRATOR_OPENING_CONTRACT_INVALID", exc) from exc
    paragraphs = [_ensure_terminal_punctuation(paragraph) for paragraph in model.paragraphs if _trim_sentence(paragraph)]
    if len(paragraphs) < 3:
        raise StoryAgentContractError("NARRATOR_OPENING_CONTRACT_INVALID", "paragraphs:min_length")
    return cast(NarratorOpeningOutput, {"paragraphs": paragraphs[:4]})
