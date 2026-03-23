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


class StoryRevealScheduleEntry(TypedDict):
    thread_index: int
    min_progress: float


class StoryBeatEntry(TypedDict):
    beat_id: str
    summary: str
    min_progress: float


class StoryVillainEntry(TypedDict):
    name: str
    motive: str
    means: str
    opportunity: str


class TimedStoryEventEntry(TypedDict):
    event_id: str
    summary: str
    min_turn: int
    location: str
    participants: list[str]


class CluePlacementEntry(TypedDict):
    item_id: str
    room_id: str
    clue_text: str
    hidden_reason: str


class StoryBootstrapCritique(TypedDict):
    verdict: str
    continuity_summary: str
    issues: list[str]


class StoryBootstrapOutput(TypedDict):
    protagonist_name: str
    protagonist_background: str
    assistant_name: str
    actionable_objective: str
    primary_goal: str
    secondary_goals: list[str]
    expanded_outline: str
    story_beats: list[StoryBeatEntry]
    villains: list[StoryVillainEntry]
    timed_events: list[TimedStoryEventEntry]
    clue_placements: list[CluePlacementEntry]
    hidden_threads: list[str]
    reveal_schedule: list[StoryRevealScheduleEntry]
    contacts: list[CharacterContact]
    opening_paragraphs: list[str]


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


class RoomPresentationEntry(TypedDict):
    room_id: str
    long: str
    short: str


class RoomPresentationOutput(TypedDict):
    rooms: list[RoomPresentationEntry]


class _StoryArchitectModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protagonist_name: str = Field(min_length=1, max_length=80)
    protagonist_background: str = Field(min_length=1, max_length=500)
    secrets_to_hide: list[str] = Field(default_factory=list, max_length=8)
    tone: str = Field(min_length=1, max_length=40)


class _StoryArchitectSingleSecretModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protagonist_name: str = Field(min_length=1, max_length=80)
    protagonist_background: str = Field(min_length=1, max_length=500)
    secrets_to_hide: str = Field(min_length=1, max_length=500)
    tone: str = Field(min_length=1, max_length=40)


class _CharacterContactModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=60)
    trait: str = Field(min_length=1, max_length=60)


class _CharacterDesignerModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contacts: list[_CharacterContactModel] = Field(min_length=1, max_length=8)


class _RevealScheduleEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    thread_index: int = Field(ge=0)
    min_progress: float = Field(ge=0.0, le=1.0)


class _StoryBeatEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    beat_id: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=240)
    min_progress: float = Field(ge=0.0, le=1.0)


class _StoryVillainEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=80)
    motive: str = Field(min_length=1, max_length=240)
    means: str = Field(min_length=1, max_length=240)
    opportunity: str = Field(min_length=1, max_length=240)


class _TimedStoryEventEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=240)
    min_turn: int = Field(ge=0, le=200)
    location: str = Field(min_length=1, max_length=80)
    participants: list[str] = Field(default_factory=list, max_length=8)


class _CluePlacementEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item_id: str = Field(min_length=1, max_length=80)
    room_id: str = Field(min_length=1, max_length=80)
    clue_text: str = Field(min_length=1, max_length=300)
    hidden_reason: str = Field(min_length=1, max_length=240)


class _StoryBootstrapModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protagonist_name: str = Field(min_length=1, max_length=80)
    protagonist_background: str = Field(min_length=1, max_length=500)
    assistant_name: str = Field(min_length=1, max_length=80)
    actionable_objective: str = Field(min_length=1, max_length=300)
    primary_goal: str = Field(min_length=1, max_length=300)
    secondary_goals: list[str] = Field(default_factory=list, max_length=4)
    expanded_outline: str = Field(min_length=1, max_length=1200)
    story_beats: list[_StoryBeatEntryModel] = Field(default_factory=list, min_length=3, max_length=8)
    villains: list[_StoryVillainEntryModel] = Field(default_factory=list, min_length=1, max_length=4)
    timed_events: list[_TimedStoryEventEntryModel] = Field(default_factory=list, max_length=8)
    clue_placements: list[_CluePlacementEntryModel] = Field(default_factory=list, max_length=12)
    hidden_threads: list[str] = Field(default_factory=list, max_length=6)
    reveal_schedule: list[_RevealScheduleEntryModel] = Field(default_factory=list, max_length=6)
    contacts: list[_CharacterContactModel] = Field(min_length=1, max_length=8)
    opening_paragraphs: list[str] = Field(min_length=3, max_length=4)


class _PlotDesignerModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assistant_name: str = Field(min_length=1, max_length=80)
    actionable_objective: str = Field(min_length=1, max_length=300)


class _NarratorOpeningModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    paragraphs: list[str] = Field(min_length=3, max_length=4)


class _RoomPresentationEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    room_id: str = Field(min_length=1, max_length=80)
    long: str = Field(min_length=1, max_length=900)
    short: str = Field(min_length=1, max_length=260)


class _RoomPresentationModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rooms: list[_RoomPresentationEntryModel] = Field(min_length=1, max_length=64)


class _StoryBootstrapCritiqueModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: str = Field(min_length=1, max_length=40)
    continuity_summary: str = Field(min_length=1, max_length=400)
    issues: list[str] = Field(default_factory=list, max_length=8)


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


_OPENING_DIRECTIVE_LABELS = (
    "room name:",
    "room description:",
    "items:",
    "exits:",
    "npc interactions:",
    "background events:",
)


def _looks_like_opening_directive_paragraph(value: str) -> bool:
    normalized = _trim_sentence(value).lower()
    if not normalized:
        return False
    matches = sum(1 for label in _OPENING_DIRECTIVE_LABELS if label in normalized)
    return matches >= 2


def _ensure_terminal_punctuation(text: str) -> str:
    cleaned = _trim_sentence(text)
    if not cleaned:
        return ""
    if cleaned[-1] in ".!?":
        return cleaned
    return f"{cleaned}."


def _is_placeholder_contact_name(name: str) -> bool:
    return re.fullmatch(r"(premise|scene|outline|characters)\s*:?", name.strip().lower()) is not None


def _validate_story_architect_payload(payload: dict) -> _StoryArchitectModel:
    try:
        return _StoryArchitectModel.model_validate(payload)
    except ValidationError:
        try:
            single_secret_model = _StoryArchitectSingleSecretModel.model_validate(payload)
        except ValidationError as second_exc:
            raise _raise_contract_error("STORY_ARCHITECT_CONTRACT_INVALID", second_exc) from second_exc
        normalized_payload = single_secret_model.model_dump(mode="python")
        normalized_payload["secrets_to_hide"] = [normalized_payload["secrets_to_hide"]]
        try:
            return _StoryArchitectModel.model_validate(normalized_payload)
        except ValidationError as normalized_exc:
            raise _raise_contract_error("STORY_ARCHITECT_CONTRACT_INVALID", normalized_exc) from normalized_exc


def parse_story_architect_output(payload: dict) -> StoryArchitectOutput:
    model = _validate_story_architect_payload(payload)
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


def parse_story_bootstrap_output(payload: dict) -> StoryBootstrapOutput:
    try:
        model = _StoryBootstrapModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("STORY_BOOTSTRAP_CONTRACT_INVALID", exc) from exc
    parsed = model.model_dump(mode="python")
    contacts = parse_character_designer_output({"contacts": parsed["contacts"]})["contacts"]
    normalized = {
        "protagonist_name": _strip_label(str(parsed["protagonist_name"]), ("name", "protagonist")),
        "protagonist_background": _ensure_terminal_punctuation(
            _strip_label(str(parsed["protagonist_background"]), ("background", "history"))
        ),
        "assistant_name": _strip_label(str(parsed["assistant_name"]), ("assistant_name", "assistant", "name")),
        "actionable_objective": _ensure_terminal_punctuation(
            _strip_label(str(parsed["actionable_objective"]), ("actionable_objective", "objective"))
        ),
        "primary_goal": _ensure_terminal_punctuation(
            _strip_label(str(parsed["primary_goal"]), ("primary_goal", "primary", "goal"))
        ),
        "secondary_goals": [
            _ensure_terminal_punctuation(str(goal))
            for goal in parsed["secondary_goals"]
            if _trim_sentence(str(goal))
        ],
        "expanded_outline": _ensure_terminal_punctuation(
            _strip_label(str(parsed["expanded_outline"]), ("expanded_outline", "outline"))
        ),
        "story_beats": [
            {
                "beat_id": _trim_sentence(str(entry["beat_id"])),
                "summary": _ensure_terminal_punctuation(str(entry["summary"])),
                "min_progress": float(entry["min_progress"]),
            }
            for entry in parsed["story_beats"]
            if _trim_sentence(str(entry["beat_id"])) and _trim_sentence(str(entry["summary"]))
        ],
        "villains": [
            {
                "name": _strip_label(str(entry["name"]), ("name", "villain")),
                "motive": _ensure_terminal_punctuation(str(entry["motive"])),
                "means": _ensure_terminal_punctuation(str(entry["means"])),
                "opportunity": _ensure_terminal_punctuation(str(entry["opportunity"])),
            }
            for entry in parsed["villains"]
            if _trim_sentence(str(entry["name"]))
        ],
        "timed_events": [
            {
                "event_id": _trim_sentence(str(entry["event_id"])),
                "summary": _ensure_terminal_punctuation(str(entry["summary"])),
                "min_turn": int(entry["min_turn"]),
                "location": _trim_sentence(str(entry["location"])),
                "participants": [
                    _trim_sentence(str(name))
                    for name in entry["participants"]
                    if _trim_sentence(str(name))
                ],
            }
            for entry in parsed["timed_events"]
            if _trim_sentence(str(entry["event_id"])) and _trim_sentence(str(entry["location"]))
        ],
        "clue_placements": [
            {
                "item_id": _trim_sentence(str(entry["item_id"])),
                "room_id": _trim_sentence(str(entry["room_id"])),
                "clue_text": _ensure_terminal_punctuation(str(entry["clue_text"])),
                "hidden_reason": _ensure_terminal_punctuation(str(entry["hidden_reason"])),
            }
            for entry in parsed["clue_placements"]
            if _trim_sentence(str(entry["item_id"])) and _trim_sentence(str(entry["room_id"]))
        ],
        "hidden_threads": [
            _ensure_terminal_punctuation(str(thread))
            for thread in parsed["hidden_threads"]
            if _trim_sentence(str(thread))
        ],
        "reveal_schedule": [
            {
                "thread_index": int(entry["thread_index"]),
                "min_progress": float(entry["min_progress"]),
            }
            for entry in parsed["reveal_schedule"]
        ],
        "contacts": contacts,
        "opening_paragraphs": parse_narrator_opening_output({"paragraphs": parsed["opening_paragraphs"]})["paragraphs"],
    }
    if not normalized["protagonist_name"]:
        raise StoryAgentContractError("STORY_BOOTSTRAP_CONTRACT_INVALID", "protagonist_name:min_length")
    if not normalized["assistant_name"]:
        raise StoryAgentContractError("STORY_BOOTSTRAP_CONTRACT_INVALID", "assistant_name:min_length")
    if not normalized["actionable_objective"]:
        raise StoryAgentContractError("STORY_BOOTSTRAP_CONTRACT_INVALID", "actionable_objective:min_length")
    if not normalized["primary_goal"]:
        raise StoryAgentContractError("STORY_BOOTSTRAP_CONTRACT_INVALID", "primary_goal:min_length")
    if not normalized["expanded_outline"]:
        raise StoryAgentContractError("STORY_BOOTSTRAP_CONTRACT_INVALID", "expanded_outline:min_length")
    if not normalized["story_beats"]:
        raise StoryAgentContractError("STORY_BOOTSTRAP_CONTRACT_INVALID", "story_beats:min_length")
    if not normalized["villains"]:
        raise StoryAgentContractError("STORY_BOOTSTRAP_CONTRACT_INVALID", "villains:min_length")
    return cast(StoryBootstrapOutput, normalized)


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
    normalized_payload = payload
    if "paragraphs" not in normalized_payload:
        draft = normalized_payload.get("draft")
        if isinstance(draft, dict) and "paragraphs" in draft:
            normalized_payload = dict(draft)
    try:
        model = _NarratorOpeningModel.model_validate(normalized_payload)
    except ValidationError as exc:
        raise _raise_contract_error("NARRATOR_OPENING_CONTRACT_INVALID", exc) from exc
    paragraphs = [
        _ensure_terminal_punctuation(paragraph)
        for paragraph in model.paragraphs
        if _trim_sentence(paragraph) and not _looks_like_opening_directive_paragraph(paragraph)
    ]
    if len(paragraphs) < 3:
        raise StoryAgentContractError("NARRATOR_OPENING_CONTRACT_INVALID", "paragraphs:min_length")
    return cast(NarratorOpeningOutput, {"paragraphs": paragraphs[:4]})


def parse_room_presentation_output(payload: dict, room_ids: tuple[str, ...]) -> RoomPresentationOutput:
    try:
        model = _RoomPresentationModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("ROOM_PRESENTATION_CONTRACT_INVALID", exc) from exc
    parsed = model.model_dump(mode="python")
    allowed_ids = set(room_ids)
    normalized_rooms: list[RoomPresentationEntry] = []
    seen_ids: set[str] = set()
    for room in parsed["rooms"]:
        room_id = _trim_sentence(str(room["room_id"]))
        if room_id not in allowed_ids or room_id in seen_ids:
            continue
        long_value = _ensure_terminal_punctuation(str(room["long"]))
        short_value = _ensure_terminal_punctuation(str(room["short"]))
        if not long_value or not short_value:
            continue
        seen_ids.add(room_id)
        normalized_rooms.append({"room_id": room_id, "long": long_value, "short": short_value})
    if len(normalized_rooms) < len(room_ids):
        raise StoryAgentContractError("ROOM_PRESENTATION_CONTRACT_INVALID", "rooms:missing_required_room_ids")
    return cast(RoomPresentationOutput, {"rooms": normalized_rooms})


def parse_story_bootstrap_critique_output(payload: dict) -> StoryBootstrapCritique:
    try:
        model = _StoryBootstrapCritiqueModel.model_validate(payload)
    except ValidationError as exc:
        raise _raise_contract_error("STORY_BOOTSTRAP_CRITIQUE_CONTRACT_INVALID", exc) from exc
    parsed = model.model_dump(mode="python")
    normalized = {
        "verdict": _trim_sentence(str(parsed["verdict"])).lower(),
        "continuity_summary": _ensure_terminal_punctuation(str(parsed["continuity_summary"])),
        "issues": [_ensure_terminal_punctuation(str(issue)) for issue in parsed["issues"] if _trim_sentence(str(issue))],
    }
    if normalized["verdict"] not in {"accepted", "revise"}:
        raise StoryAgentContractError("STORY_BOOTSTRAP_CRITIQUE_CONTRACT_INVALID", "verdict:invalid_choice")
    return cast(StoryBootstrapCritique, normalized)
