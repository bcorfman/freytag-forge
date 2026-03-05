from __future__ import annotations

from storygame.engine.parser import Action, ActionKind
from storygame.engine.state import Event, GameState, Room


def _find_exit(room: Room, target: str) -> str | None:
    if target in room.exits:
        return room.exits[target]
    for _direction, destination in room.exits.items():
        if destination == target:
            return destination
    return None


def apply_action(state: GameState, action: Action, rng) -> tuple[GameState, list[Event]]:
    next_state = state.clone()
    next_state.turn_index += 1
    events: list[Event] = []

    room = next_state.world.rooms[next_state.player.location]

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
        return next_state, events

    if action.kind == ActionKind.HELP:
        events.append(
            Event(
                type="help",
                message_key="help",
                entities=("help",),
                turn_index=next_state.turn_index,
            )
        )
        return next_state, events

    if action.kind == ActionKind.INVENTORY:
        events.append(
            Event(
                type="inventory",
                message_key="inventory",
                entities=next_state.player.inventory,
                turn_index=next_state.turn_index,
            )
        )
        return next_state, events

    if action.kind == ActionKind.MOVE:
        destination = _find_exit(room, action.target)
        if destination is None:
            events.append(
                Event(
                    type="move_failed",
                    message_key="move_failed_unknown_destination",
                    entities=(action.target,),
                    tags=("validation",),
                    turn_index=next_state.turn_index,
                )
            )
            return next_state, events

        direction = next(
            (key for key, value in room.exits.items() if value == destination),
            action.target,
        )
        lock_key = room.locked_exits.get(action.target) or room.locked_exits.get(direction)

        if lock_key is not None and lock_key not in next_state.player.inventory:
            events.append(
                Event(
                    type="move_failed",
                    message_key="move_failed_locked_exit",
                    entities=(action.target, lock_key),
                    tags=("validation", "locked"),
                    turn_index=next_state.turn_index,
                )
            )
            return next_state, events

        next_state.player.location = destination
        events.append(
            Event(
                type="move",
                message_key="move_success",
                entities=(action.target, destination),
                tags=("world",),
                turn_index=next_state.turn_index,
            )
        )
        return next_state, events

    if action.kind == ActionKind.TAKE:
        if action.target not in room.item_ids:
            events.append(
                Event(
                    type="take_failed",
                    message_key="take_failed_missing",
                    entities=(action.target,),
                    tags=("validation",),
                    turn_index=next_state.turn_index,
                )
            )
            return next_state, events

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
            return next_state, events

        room.item_ids = tuple(item_id for item_id in room.item_ids if item_id != action.target)
        next_state.player.inventory = tuple(list(next_state.player.inventory) + [action.target])

        events.append(
            Event(
                type="take",
                message_key="take_success",
                entities=(action.target,),
                delta_progress=item.delta_progress,
                delta_tension=0.02,
                tags=("world", "quest_item" if "quest" in item.tags else "world_item"),
                turn_index=next_state.turn_index,
            )
        )
        return next_state, events

    if action.kind == ActionKind.TALK:
        npc_id = action.target
        if npc_id not in room.npc_ids:
            events.append(
                Event(
                    type="talk_failed",
                    message_key="talk_failed_missing",
                    entities=(action.target,),
                    tags=("validation",),
                    turn_index=next_state.turn_index,
                )
            )
            return next_state, events

        npc = next_state.world.npcs[npc_id]
        flag_key = f"talked_{npc_id}"
        previous_talk = next_state.player.flags.get(flag_key, False)
        if not previous_talk:
            next_state.player.flags[flag_key] = True

        events.append(
            Event(
                type="talk",
                message_key="talk_success",
                entities=(npc_id,),
                delta_progress=0.0 if previous_talk else npc.delta_progress,
                delta_tension=0.03,
                tags=("world", "dialog"),
                turn_index=next_state.turn_index,
                metadata={"dialog": npc.dialogue},
            )
        )
        return next_state, events

    if action.kind == ActionKind.USE:
        payload = action.target
        if ":" in payload:
            item_id, target = payload.split(":", 1)
        else:
            item_id, target = payload, ""

        if item_id not in next_state.player.inventory:
            events.append(
                Event(
                    type="use_failed",
                    message_key="use_failed_missing_item",
                    entities=(item_id,),
                    tags=("validation",),
                    turn_index=next_state.turn_index,
                )
            )
            return next_state, events

        events.append(
            Event(
                type="use",
                message_key="use_success",
                entities=(item_id, target) if target else (item_id,),
                delta_tension=0.01,
                tags=("world",),
                turn_index=next_state.turn_index,
            )
        )
        return next_state, events

    events.append(
        Event(
            type="unknown",
            message_key="unknown_command",
            entities=(action.raw,),
            tags=("validation",),
            turn_index=next_state.turn_index,
        )
    )
    return next_state, events
