from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _clamp_unit(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


@dataclass(frozen=True)
class Event:
    type: str
    entities: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    delta_progress: float = 0.0
    delta_tension: float = 0.0
    message_key: str = ""
    turn_index: int = 0
    timestamp: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_summary(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "entities": list(self.entities),
            "tags": list(self.tags),
            "message_key": self.message_key,
            "turn_index": self.turn_index,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class EventLog:
    events: tuple[Event, ...] = ()

    def append(self, event: Event) -> EventLog:
        return EventLog(events=self.events + (event,))

    def extend(self, new_events: list[Event] | tuple[Event, ...]) -> EventLog:
        return EventLog(events=self.events + tuple(new_events))

    def tail(self, count: int) -> tuple[Event, ...]:
        return self.events[-count:]

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)


@dataclass
class PlayerState:
    location: str
    inventory: tuple[str, ...] = ()
    flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class Item:
    id: str
    name: str
    description: str
    portable: bool = True
    tags: tuple[str, ...] = ()
    delta_progress: float = 0.0
    delta_tension: float = 0.0


@dataclass
class Npc:
    id: str
    name: str
    description: str
    dialogue: str
    identity: str = ""
    pronouns: str = "they/them"
    tags: tuple[str, ...] = ()
    delta_progress: float = 0.0
    delta_tension: float = 0.0


@dataclass
class Room:
    id: str
    name: str
    description: str
    exits: dict[str, str] = field(default_factory=dict)
    locked_exits: dict[str, str] = field(default_factory=dict)
    item_ids: tuple[str, ...] = ()
    npc_ids: tuple[str, ...] = ()


@dataclass
class WorldState:
    rooms: dict[str, Room]
    items: dict[str, Item]
    npcs: dict[str, Npc]


@dataclass
class GameState:
    seed: int
    player: PlayerState
    world: WorldState
    progress: float = 0.0
    tension: float = 0.35
    turn_index: int = 0
    event_log: EventLog = field(default_factory=EventLog)
    beat_history: tuple[str, ...] = ()
    active_goal: str = "Follow the bell signal and uncover the old conspiracy."

    def clone(self) -> GameState:
        return copy.deepcopy(self)

    def with_progress(self, progress: float) -> GameState:
        self.progress = _clamp_unit(progress)
        return self

    def with_tension(self, tension: float) -> GameState:
        self.tension = _clamp_unit(tension)
        return self

    def append_event(self, event: Event) -> None:
        self.event_log = self.event_log.append(event)

    def append_events(self, events: list[Event] | tuple[Event, ...]) -> None:
        self.event_log = self.event_log.extend(events)

    def append_beat(self, beat_type: str) -> None:
        self.beat_history = self.beat_history + (beat_type,)

    def replay_signature(self) -> str:
        data = {
            "turn_index": self.turn_index,
            "location": self.player.location,
            "inventory": self.player.inventory,
            "progress": round(self.progress, 6),
            "tension": round(self.tension, 6),
            "event_log": [event.to_summary() for event in self.event_log],
            "beat_history": self.beat_history,
            "flags": self.player.flags,
            "room_items": {
                room_id: room.item_ids for room_id, room in sorted(self.world.rooms.items())
            },
        }
        payload = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
