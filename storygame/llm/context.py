from __future__ import annotations

from dataclasses import dataclass

from storygame.engine.mystery import filtered_inventory, room_item_groups
from storygame.engine.parser import Action
from storygame.engine.state import EventLog, GameState, Npc
from storygame.plot.freytag import get_phase

MAX_RECENT_EVENTS = 5
MAX_VISIBLE_ITEMS = 6
MAX_INVENTORY_ITEMS = 8
MAX_EVENT_MESSAGE_LEN = 120
MAX_NPC_FACTS = 12
MAX_NPC_DESCRIPTION_LEN = 100
MAX_MEMORY_FRAGMENTS = 3
MAX_MEMORY_FRAGMENT_LEN = 220

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
    npc_facts: tuple[dict, ...]
    exits: tuple[str, ...]
    inventory: tuple[str, ...]
    recent_events: tuple[dict, ...]
    phase: str
    tension: float
    beat: str
    goal: str
    action: str
    memory_fragments: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "room_name": self.room_name,
            "room_description": self.room_description,
            "visible_items": list(self.visible_items),
            "visible_npcs": list(self.visible_npcs),
            "npc_facts": list(self.npc_facts),
            "exits": list(self.exits),
            "inventory": list(self.inventory),
            "recent_events": list(self.recent_events),
            "phase": self.phase,
            "tension": self.tension,
            "beat": self.beat,
            "goal": self.goal,
            "action": self.action,
            "memory_fragments": list(self.memory_fragments),
            "constraints": list(HARD_CONSTRAINTS),
        }


def _short_message(value: str) -> str:
    if len(value) <= MAX_EVENT_MESSAGE_LEN:
        return value
    return value[: MAX_EVENT_MESSAGE_LEN - 3] + "..."


def _short_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _npc_fact(npc: Npc, location: str) -> dict[str, str]:
    return {
        "id": npc.id,
        "name": npc.name,
        "pronouns": npc.pronouns,
        "identity": _short_text(npc.identity, MAX_NPC_DESCRIPTION_LEN),
        "description": _short_text(npc.description, MAX_NPC_DESCRIPTION_LEN),
        "location": location,
    }


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


def _npc_locations(state: GameState) -> dict[str, str]:
    locations: dict[str, str] = {}
    for room_id, room in state.world.rooms.items():
        for npc_id in room.npc_ids:
            locations[npc_id] = room_id
    return locations


def _summarize_npc_facts(state: GameState) -> tuple[dict, ...]:
    locations = _npc_locations(state)
    npc_ids = sorted(state.world.npcs.keys())
    return tuple(_npc_fact(state.world.npcs[npc_id], locations.get(npc_id, "")) for npc_id in npc_ids[:MAX_NPC_FACTS])


def build_narration_context(
    state: GameState,
    action: Action,
    beat: str,
    memory_fragments: tuple[str, ...] = (),
) -> NarrationContext:
    room = state.world.rooms[state.player.location]
    visible_items, _junk_count = room_item_groups(state, room)

    return NarrationContext(
        room_name=room.name,
        room_description=room.description,
        visible_items=visible_items[:MAX_VISIBLE_ITEMS],
        visible_npcs=room.npc_ids,
        npc_facts=_summarize_npc_facts(state),
        exits=tuple(sorted(room.exits.keys())),
        inventory=filtered_inventory(state)[:MAX_INVENTORY_ITEMS],
        memory_fragments=tuple(
            _short_text(frag, MAX_MEMORY_FRAGMENT_LEN) for frag in memory_fragments[:MAX_MEMORY_FRAGMENTS]
        ),
        recent_events=_summarize_recent_events(state.event_log),
        phase=get_phase(state.progress),
        tension=state.tension,
        beat=beat,
        goal=state.active_goal,
        action=action.raw,
    )
