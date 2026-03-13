from __future__ import annotations

from storygame.engine.facts import (
    apply_fact_ops,
    event_fact_ops,
    player_inventory,
    player_location,
    rebuild_facts_from_legacy_views,
    room_items,
    room_npcs,
    room_paths,
)
from storygame.engine.mystery import npc_talk_message, take_item_message
from storygame.engine.parser import Action, ActionKind
from storygame.engine.state import Event, GameState


def _find_exit(state: GameState, room_id: str, target: str) -> tuple[str, str] | None:
    exits = room_paths(state, room_id)
    if target in exits:
        return target, exits[target]
    for direction, destination in exits.items():
        if destination == target:
            return direction, destination
    return None


def _use_event(
    turn_index: int,
    entities: tuple[str, ...],
    message: str,
    delta_progress: float = 0.0,
    fact_ops: list[dict[str, object]] | None = None,
) -> Event:
    return Event(
        type="use",
        message_key=message,
        entities=entities,
        delta_progress=delta_progress,
        delta_tension=0.01,
        tags=("world",),
        turn_index=turn_index,
        metadata={"fact_ops": fact_ops or []},
    )


def _resolve_use(state: GameState, item_id: str, target: str) -> Event:
    turn_index = state.turn_index
    target_label = (item_id, target) if target else (item_id,)
    target_fragment = target if target else "self"
    flag = f"used_{item_id}_{target_fragment}".replace(" ", "_")

    if state.world_facts.holds("flag", "player", flag):
        return _use_event(turn_index, target_label, "use_success")

    item = state.world.items.get(item_id)
    delta_progress = 0.0
    if item is not None:
        if item.kind == "tool":
            delta_progress = 0.02
        elif item.kind == "clue":
            delta_progress = 0.04
        elif item.kind == "evidence":
            delta_progress = 0.06

    return _use_event(
        turn_index,
        target_label,
        "use_success",
        delta_progress=delta_progress,
        fact_ops=[{"op": "assert", "fact": ("flag", "player", flag)}],
    )


def apply_action(state: GameState, action: Action, rng) -> tuple[GameState, list[Event]]:
    next_state = state.clone()
    rebuild_facts_from_legacy_views(next_state)
    next_state.turn_index += 1
    events: list[Event] = []

    room_id = player_location(next_state)
    def _commit() -> tuple[GameState, list[Event]]:
        for event in events:
            ops = event_fact_ops(event)
            if ops:
                apply_fact_ops(next_state, ops)
        return next_state, events

    if action.kind == ActionKind.LOOK:
        events.append(
            Event(
                type="look",
                message_key="look",
                entities=(next_state.player.location,),
                tags=("observation",),
                turn_index=next_state.turn_index,
            )
        )
        return _commit()

    if action.kind == ActionKind.HELP:
        events.append(
            Event(
                type="help",
                message_key="help",
                entities=("help",),
                turn_index=next_state.turn_index,
            )
        )
        return _commit()

    if action.kind == ActionKind.INVENTORY:
        events.append(
            Event(
                type="inventory",
                message_key="inventory",
                entities=player_inventory(next_state),
                turn_index=next_state.turn_index,
            )
        )
        return _commit()

    if action.kind == ActionKind.MOVE:
        exit_result = _find_exit(next_state, room_id, action.target)
        if exit_result is None:
            events.append(
                Event(
                    type="move_failed",
                    message_key="move_failed_unknown_destination",
                    entities=(action.target,),
                    tags=("validation",),
                    turn_index=next_state.turn_index,
                )
            )
            return _commit()

        direction, destination = exit_result
        locked_facts = next_state.world_facts.query("locked", direction, room_id, None)
        lock_key = locked_facts[0][3] if locked_facts else None

        if lock_key is not None and lock_key not in player_inventory(next_state):
            events.append(
                Event(
                    type="move_failed",
                    message_key="move_failed_locked_exit",
                    entities=(action.target, lock_key),
                    tags=("validation", "locked"),
                    turn_index=next_state.turn_index,
                )
            )
            return _commit()

        events.append(
            Event(
                type="move",
                message_key="move_success",
                entities=(action.target, destination),
                tags=("world",),
                turn_index=next_state.turn_index,
                metadata={
                    "fact_ops": [
                        {"op": "retract", "fact": ("at", "player", room_id)},
                        {"op": "assert", "fact": ("at", "player", destination)},
                    ]
                },
            )
        )
        return _commit()

    if action.kind == ActionKind.TAKE:
        if action.target not in room_items(next_state, room_id):
            events.append(
                Event(
                    type="take_failed",
                    message_key="take_failed_missing",
                    entities=(action.target,),
                    tags=("validation",),
                    turn_index=next_state.turn_index,
                )
            )
            return _commit()

        item = next_state.world.items[action.target]
        if not item.portable:
            events.append(
                Event(
                    type="take_failed",
                    message_key="take_failed_not_portable",
                    entities=(action.target,),
                    turn_index=next_state.turn_index,
                )
            )
            return _commit()

        events.append(
            Event(
                type="take",
                message_key=take_item_message(item),
                entities=(action.target,),
                delta_progress=item.delta_progress,
                delta_tension=0.02,
                tags=("world", "quest_item" if "quest" in item.tags else "world_item"),
                turn_index=next_state.turn_index,
                metadata={
                    "item_kind": item.kind,
                    "item_name": item.name,
                    "fact_ops": [
                        {"op": "retract", "fact": ("room_item", room_id, action.target)},
                        {"op": "assert", "fact": ("holding", "player", action.target)},
                    ],
                },
            )
        )
        return _commit()

    if action.kind == ActionKind.TALK:
        npc_id = action.target
        if npc_id not in room_npcs(next_state, room_id):
            events.append(
                Event(
                    type="talk_failed",
                    message_key="talk_failed_missing",
                    entities=(action.target,),
                    tags=("validation",),
                    turn_index=next_state.turn_index,
                )
            )
            return _commit()

        npc = next_state.world.npcs[npc_id]
        flag_key = f"talked_{npc_id}"
        previous_talk = next_state.world_facts.holds("flag", "player", flag_key)

        talk_line = npc_talk_message(next_state, npc, not previous_talk)
        events.append(
            Event(
                type="talk",
                message_key=talk_line,
                entities=(npc_id,),
                delta_progress=0.0 if previous_talk else npc.delta_progress,
                delta_tension=0.03,
                tags=("world", "dialog"),
                turn_index=next_state.turn_index,
                metadata={
                    "dialogue": talk_line,
                    "npc_id": npc_id,
                    "first_talk": not previous_talk,
                    "knowledge_source": npc.knowledge_source,
                    "fact_ops": ([] if previous_talk else [{"op": "assert", "fact": ("flag", "player", flag_key)}]),
                },
            )
        )
        return _commit()

    if action.kind == ActionKind.USE:
        payload = action.target
        if ":" in payload:
            item_id, target = payload.split(":", 1)
        else:
            item_id, target = payload, ""

        if item_id not in player_inventory(next_state):
            events.append(
                Event(
                    type="use_failed",
                    message_key="use_failed_missing_item",
                    entities=(item_id,),
                    tags=("validation",),
                    turn_index=next_state.turn_index,
                )
            )
            return _commit()

        events.append(_resolve_use(next_state, item_id, target))
        return _commit()

    events.append(
        Event(
            type="unknown",
            message_key="unknown_command",
            entities=(action.raw,),
            tags=("validation",),
            turn_index=next_state.turn_index,
        )
    )
    return _commit()
