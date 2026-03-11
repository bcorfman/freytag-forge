from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from random import Random
from typing import TypedDict

import yaml
from pydantic import BaseModel, ConfigDict, Field

from storygame.engine.facts import apply_fact_ops, player_inventory, player_location, rebuild_facts_from_legacy_views
from storygame.engine.state import Event, GameState
from storygame.plot.beat_manager import Beat


class ConditionSpec(TypedDict):
    event: str
    room: str
    action_type: str
    entity: str
    item_in_inventory: str
    flag_is_true: str
    progress_at_least: float
    location_is: str


class SequenceSpec(TypedDict):
    within_turns: int
    steps: tuple[ConditionSpec, ...]


class TriggerSpec(TypedDict):
    min_turn: int
    cooldown_turns: int
    all: tuple[ConditionSpec, ...]
    any: tuple[ConditionSpec, ...]
    not_conditions: tuple[ConditionSpec, ...]
    sequence: SequenceSpec | None


class EffectSpec(TypedDict):
    delta_progress: float
    delta_tension: float
    set_flags: tuple[str, ...]
    clear_flags: tuple[str, ...]


class IncidentSpec(TypedDict):
    incident_id: str
    once_flag: str
    beat_tags: tuple[str, ...]
    message_key: str
    entities: tuple[str, ...]
    effects: EffectSpec
    triggers: TriggerSpec


class ConditionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: str = ""
    room: str = ""
    action_type: str = ""
    entity: str = ""
    item_in_inventory: str = ""
    flag_is_true: str = ""
    progress_at_least: float = -1.0
    location_is: str = ""


class SequenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    within_turns: int = Field(default=0, ge=0)
    steps: tuple[ConditionModel, ...] = ()


class TriggerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    min_turn: int = Field(default=0, ge=0)
    cooldown_turns: int = Field(default=0, ge=0)
    all: tuple[ConditionModel, ...] = ()
    any: tuple[ConditionModel, ...] = ()
    not_conditions: tuple[ConditionModel, ...] = Field(default=(), alias="not")
    sequence: SequenceModel | None = None


class EffectModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delta_progress: float = 0.0
    delta_tension: float = 0.0
    set_flags: tuple[str, ...] = ()
    clear_flags: tuple[str, ...] = ()


class IncidentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    once_flag: str = ""
    beat_tags: tuple[str, ...]
    message: str
    entities: tuple[str, ...] = ()
    effects: EffectModel = Field(default_factory=EffectModel)
    triggers: TriggerModel = Field(default_factory=TriggerModel)


class IncidentConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    incidents: tuple[IncidentModel, ...]


def _condition_spec(model: ConditionModel) -> ConditionSpec:
    return {
        "event": model.event,
        "room": model.room,
        "action_type": model.action_type,
        "entity": model.entity,
        "item_in_inventory": model.item_in_inventory,
        "flag_is_true": model.flag_is_true,
        "progress_at_least": model.progress_at_least,
        "location_is": model.location_is,
    }


def _sequence_spec(model: SequenceModel | None) -> SequenceSpec | None:
    if model is None:
        return None
    return {
        "within_turns": model.within_turns,
        "steps": tuple(_condition_spec(step) for step in model.steps),
    }


def _trigger_spec(model: TriggerModel) -> TriggerSpec:
    return {
        "min_turn": model.min_turn,
        "cooldown_turns": model.cooldown_turns,
        "all": tuple(_condition_spec(condition) for condition in model.all),
        "any": tuple(_condition_spec(condition) for condition in model.any),
        "not_conditions": tuple(_condition_spec(condition) for condition in model.not_conditions),
        "sequence": _sequence_spec(model.sequence),
    }


def parse_incident_specs(payload: dict[str, object]) -> tuple[IncidentSpec, ...]:
    model = IncidentConfigModel.model_validate(payload)
    return tuple(
        {
            "incident_id": incident.id,
            "once_flag": incident.once_flag,
            "beat_tags": incident.beat_tags,
            "message_key": incident.message,
            "entities": incident.entities,
            "effects": {
                "delta_progress": incident.effects.delta_progress,
                "delta_tension": incident.effects.delta_tension,
                "set_flags": incident.effects.set_flags,
                "clear_flags": incident.effects.clear_flags,
            },
            "triggers": _trigger_spec(incident.triggers),
        }
        for incident in model.incidents
    )


def _incidents_path() -> Path:
    return Path(__file__).resolve().parents[1] / "content" / "incidents.yaml"


@lru_cache(maxsize=1)
def load_incident_specs() -> tuple[IncidentSpec, ...]:
    payload = yaml.safe_load(_incidents_path().read_text(encoding="utf-8"))
    return parse_incident_specs(payload)


def _matches_action_event(event: Event, action_type: str, entity: str) -> bool:
    if action_type and event.type != action_type:
        return False
    return not (entity and entity not in event.entities)


def _condition_matches_turn(
    condition: ConditionSpec,
    state: GameState,
    action_events: tuple[Event, ...],
) -> bool:
    location = player_location(state)
    inventory = player_inventory(state)

    if condition["location_is"] and location != condition["location_is"]:
        return False

    if condition["item_in_inventory"] and condition["item_in_inventory"] not in inventory:
        return False

    if condition["flag_is_true"] and not state.world_facts.holds("flag", "player", condition["flag_is_true"]):
        return False

    threshold = condition["progress_at_least"]
    if threshold >= 0.0 and state.progress < threshold:
        return False

    event_name = condition["event"]
    if event_name == "player_entered_room":
        room = condition["room"]
        return any(
            event.type == "move" and len(event.entities) >= 2 and (room == "" or event.entities[1] == room)
            for event in action_events
        )

    action_type = condition["action_type"]
    if action_type:
        return any(_matches_action_event(event, action_type, condition["entity"]) for event in action_events)

    return True


def _condition_matches_event(condition: ConditionSpec, event: Event) -> bool:
    event_name = condition["event"]
    if event_name == "player_entered_room":
        room = condition["room"]
        return event.type == "move" and len(event.entities) >= 2 and (room == "" or event.entities[1] == room)

    if condition["action_type"] and event.type != condition["action_type"]:
        return False

    if condition["entity"] and condition["entity"] not in event.entities:
        return False

    return not (event_name and event_name != "player_entered_room" and event.type != event_name)


def _sequence_matches(sequence: SequenceSpec | None, state: GameState) -> bool:
    if sequence is None:
        return True

    steps = sequence["steps"]
    if not steps:
        return True

    events = state.event_log.events
    within_turns = sequence["within_turns"]
    if within_turns > 0:
        earliest_turn = max(1, state.turn_index - within_turns + 1)
        events = tuple(event for event in events if event.turn_index >= earliest_turn)

    step_index = 0
    for event in events:
        if _condition_matches_event(steps[step_index], event):
            step_index += 1
            if step_index == len(steps):
                return True

    return False


def _last_incident_turn(state: GameState, incident_id: str) -> int | None:
    for event in reversed(state.event_log.events):
        if event.type != "incident":
            continue
        if str(event.metadata.get("incident_id", "")) == incident_id:
            return event.turn_index
    return None


def _eligible(spec: IncidentSpec, state: GameState, beat: Beat, action_events: tuple[Event, ...]) -> bool:
    if not set(spec["beat_tags"]).intersection(set(beat.tags)):
        return False

    once_flag = spec["once_flag"]
    if once_flag and state.world_facts.holds("flag", "player", once_flag):
        return False

    triggers = spec["triggers"]
    if triggers["min_turn"] > 0 and state.turn_index < triggers["min_turn"]:
        return False

    cooldown_turns = triggers["cooldown_turns"]
    if cooldown_turns > 0:
        last_turn = _last_incident_turn(state, spec["incident_id"])
        if last_turn is not None and state.turn_index - last_turn < cooldown_turns:
            return False

    if triggers["all"] and not all(
        _condition_matches_turn(condition, state, action_events) for condition in triggers["all"]
    ):
        return False

    if triggers["any"] and not any(
        _condition_matches_turn(condition, state, action_events) for condition in triggers["any"]
    ):
        return False

    if triggers["not_conditions"] and any(
        _condition_matches_turn(condition, state, action_events) for condition in triggers["not_conditions"]
    ):
        return False

    return _sequence_matches(triggers["sequence"], state)


def realize_beat_incident(
    state: GameState,
    beat: Beat,
    action_events: list[Event] | tuple[Event, ...],
    rng: Random,
    incident_specs: tuple[IncidentSpec, ...] | None = None,
) -> tuple[GameState, list[Event]]:
    rebuild_facts_from_legacy_views(state)
    specs = load_incident_specs() if incident_specs is None else incident_specs
    action_tuple = tuple(action_events)
    candidates = [spec for spec in specs if _eligible(spec, state, beat, action_tuple)]
    if not candidates:
        return state, []

    chosen = candidates[rng.randrange(len(candidates))]
    next_state = state.clone()

    once_flag = chosen["once_flag"]
    fact_ops: list[dict[str, object]] = []
    if once_flag:
        fact_ops.append({"op": "assert", "fact": ("flag", "player", once_flag)})
    for flag in chosen["effects"]["set_flags"]:
        fact_ops.append({"op": "assert", "fact": ("flag", "player", flag)})
    for flag in chosen["effects"]["clear_flags"]:
        fact_ops.append({"op": "retract", "fact": ("flag", "player", flag)})

    event = Event(
        type="incident",
        message_key=chosen["message_key"],
        entities=chosen["entities"],
        tags=("plot", "incident", *chosen["beat_tags"]),
        delta_progress=chosen["effects"]["delta_progress"],
        delta_tension=chosen["effects"]["delta_tension"],
        turn_index=next_state.turn_index,
        metadata={"incident_id": chosen["incident_id"], "fact_ops": fact_ops},
    )
    if fact_ops:
        apply_fact_ops(next_state, fact_ops)
    next_state.append_event(event)
    return next_state, [event]
