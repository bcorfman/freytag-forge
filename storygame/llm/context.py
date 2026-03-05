from __future__ import annotations

from dataclasses import dataclass

from storygame.engine.parser import Action
from storygame.engine.state import EventLog, GameState
from storygame.plot.freytag import get_phase

MAX_RECENT_EVENTS = 5
MAX_VISIBLE_ITEMS = 6
MAX_INVENTORY_ITEMS = 8
MAX_EVENT_MESSAGE_LEN = 80

HARD_CONSTRAINTS = (
    "no_state_mutation",
    "do_not_invent_facts",
    "must_match_engine_context",
)


@dataclass(frozen=True)
class NarrationContext:
    room_name: str
    room_description: str
    visible_items: tuple[str, ...]
    visible_npcs: tuple[str, ...]
    exits: tuple[str, ...]
    inventory: tuple[str, ...]
    recent_events: tuple[dict, ...]
    phase: str
    tension: float
    beat: str
    goal: str
    action: str

    def as_dict(self) -> dict:
        return {
            "room_name": self.room_name,
            "room_description": self.room_description,
            "visible_items": list(self.visible_items),
            "visible_npcs": list(self.visible_npcs),
            "exits": list(self.exits),
            "inventory": list(self.inventory),
            "recent_events": list(self.recent_events),
            "phase": self.phase,
            "tension": self.tension,
            "beat": self.beat,
            "goal": self.goal,
            "action": self.action,
            "constraints": list(HARD_CONSTRAINTS),
        }


def _short_message(value: str) -> str:
    if len(value) <= MAX_EVENT_MESSAGE_LEN:
        return value
    return value[: MAX_EVENT_MESSAGE_LEN - 3] + "..."


def _summarize_recent_events(events: EventLog) -> tuple[dict, ...]:
    trimmed = events.tail(MAX_RECENT_EVENTS)
    return tuple(
        {
            "type": event.type,
            "message_key": _short_message(event.message_key),
            "entities": list(event.entities),
            "tags": list(event.tags),
            "turn_index": event.turn_index,
        }
        for event in trimmed
    )


def build_narration_context(
    state: GameState,
    action: Action,
    beat: str,
) -> NarrationContext:
    room = state.world.rooms[state.player.location]
    visible_items = tuple(item_id for item_id in room.item_ids if item_id in state.world.items)

    return NarrationContext(
        room_name=room.name,
        room_description=room.description,
        visible_items=visible_items[:MAX_VISIBLE_ITEMS],
        visible_npcs=room.npc_ids,
        exits=tuple(sorted(room.exits.keys())),
        inventory=state.player.inventory[:MAX_INVENTORY_ITEMS],
        recent_events=_summarize_recent_events(state.event_log),
        phase=get_phase(state.progress),
        tension=state.tension,
        beat=beat,
        goal=state.active_goal,
        action=action.raw,
    )
