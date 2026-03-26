from __future__ import annotations

from typing import TYPE_CHECKING

from storygame.engine.facts import player_location, room_items
from storygame.engine.state import Event, GameState

if TYPE_CHECKING:
    from storygame.llm.contracts import SemanticActionProposal


def commit_semantic_action(state: GameState, action: SemanticActionProposal) -> Event:
    action_type = str(action["action_type"]).strip()
    actor_id = str(action["actor_id"]).strip() or "player"
    target_id = str(action["target_id"]).strip()
    item_id = str(action["item_id"]).strip()
    location_id = str(action["location_id"]).strip()

    if action_type == "take_item":
        room_id = location_id or player_location(state)
        if actor_id != "player":
            raise ValueError("take_item currently supports player actor only.")
        if item_id not in room_items(state, room_id):
            raise ValueError(f"Item '{item_id}' is not available in room '{room_id}'.")
        return Event(
            type="semantic_action",
            message_key="take_item",
            entities=(actor_id, item_id, room_id),
            tags=("semantic_action", action_type),
            turn_index=state.turn_index,
            metadata={
                "action_id": str(action["action_id"]).strip(),
                "action_type": action_type,
                "actor_id": actor_id,
                "target_id": target_id,
                "item_id": item_id,
                "location_id": room_id,
                "fact_ops": [
                    {"op": "retract", "fact": ("room_item", room_id, item_id)},
                    {"op": "assert", "fact": ("holding", actor_id, item_id)},
                ],
            },
        )

    if action_type == "move_to":
        if not location_id:
            raise ValueError("move_to requires a location_id.")
        predicate = "at" if actor_id == "player" else "npc_at"
        fact = (predicate, actor_id, location_id)
        return Event(
            type="semantic_action",
            message_key="move_to",
            entities=(actor_id, location_id),
            tags=("semantic_action", action_type),
            turn_index=state.turn_index,
            metadata={
                "action_id": str(action["action_id"]).strip(),
                "action_type": action_type,
                "actor_id": actor_id,
                "target_id": target_id,
                "item_id": item_id,
                "location_id": location_id,
                "fact_ops": [{"op": "assert", "fact": fact}],
            },
        )

    return Event(
        type="semantic_action",
        message_key=action_type,
        entities=tuple(part for part in (actor_id, target_id, item_id, location_id) if part),
        tags=("semantic_action", action_type),
        turn_index=state.turn_index,
        metadata={
            "action_id": str(action["action_id"]).strip(),
            "action_type": action_type,
            "actor_id": actor_id,
            "target_id": target_id,
            "item_id": item_id,
            "location_id": location_id,
            "fact_ops": [],
        },
    )
