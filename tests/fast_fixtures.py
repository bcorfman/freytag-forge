"""Small immutable-package and cloned-runtime factories for narrow tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from storygame.engine.facts import initialize_world_facts
from storygame.engine.state import Event, GameState, Item, Npc, PlayerState, Room, WorldState


@dataclass(frozen=True)
class TinyPackage:
    """Authoring input shared safely by tests; runtime state is always a clone."""

    room_id: str = "room"
    item_id: str = "key"
    npc_id: str = "guide"


def make_tiny_package(**overrides: str) -> TinyPackage:
    values = {"room_id": "room", "item_id": "key", "npc_id": "guide", **overrides}
    return TinyPackage(**values)


def make_tiny_state(seed: int = 1, package: TinyPackage | None = None) -> GameState:
    package = package or TinyPackage()
    room = Room(
        id=package.room_id,
        name="A Tiny Room",
        description="A room made for a focused test.",
        exits={},
        item_ids=(package.item_id,),
        npc_ids=(package.npc_id,),
    )
    state = GameState(
        seed=seed,
        player=PlayerState(location=package.room_id, flags={"started": True}),
        world=WorldState(
            rooms={package.room_id: room},
            items={package.item_id: Item(package.item_id, "Test Key", "A small test key.", kind="tool")},
            npcs={package.npc_id: Npc(package.npc_id, "Guide", "A test guide.", "Ask me anything.")},
        ),
        world_package={"genre": "fixture", "facts": "authoring-only"},
        active_goal="Test the focused boundary.",
    )
    initialize_world_facts(state)
    return state


def make_persistence_state(seed: int = 1) -> GameState:
    """A two-room state suitable for serializer tests without package generation."""

    package = TinyPackage(room_id="foyer", item_id="key", npc_id="guide")
    state = make_tiny_state(seed=seed, package=package)
    state.world.rooms["next_room"] = Room(
        id="next_room",
        name="Next Room",
        description="A second room for projection tests.",
        exits={"south": "foyer"},
    )
    state.world.rooms["foyer"].exits = {"north": "next_room"}
    state.world.items["note"] = Item("note", "Test Note", "A portable note.", kind="clue")
    initialize_world_facts(state)
    return state


def clone_runtime_state(state: GameState) -> GameState:
    """Clone a runtime projection so no test can mutate the shared package."""

    return deepcopy(state)


def make_proposal(**overrides: Any) -> dict[str, Any]:
    proposal: dict[str, Any] = {
        "intent": "examine",
        "targets": [],
        "arguments": {},
        "proposed_effects": [],
        "dialogue": None,
        "narration": "",
    }
    proposal.update(overrides)
    return proposal


def make_event(event_type: str = "test", **overrides: Any) -> Event:
    values: dict[str, Any] = {"type": event_type, "message_key": "fixture event"}
    values.update(overrides)
    return Event(**values)


def make_fact(predicate: str = "flag", *terms: str) -> tuple[str, ...]:
    return (predicate, *terms) if terms else (predicate, "player", "fixture")
