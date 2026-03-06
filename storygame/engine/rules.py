from __future__ import annotations

from storygame.engine.mystery import npc_talk_message, take_item_message
from storygame.engine.parser import Action, ActionKind
from storygame.engine.state import Event, GameState, Room


def _find_exit(room: Room, target: str) -> str | None:
    if target in room.exits:
        return room.exits[target]
    for _direction, destination in room.exits.items():
        if destination == target:
            return destination
    return None


def _use_event(turn_index: int, entities: tuple[str, ...], message: str, delta_progress: float = 0.0) -> Event:
    return Event(
        type="use",
        message_key=message,
        entities=entities,
        delta_progress=delta_progress,
        delta_tension=0.01,
        tags=("world",),
        turn_index=turn_index,
    )


def _resolve_use(state: GameState, item_id: str, target: str) -> Event:
    turn_index = state.turn_index
    inventory = state.player.inventory
    location = state.player.location
    target_label = (item_id, target) if target else (item_id,)

    map_and_lens = {item_id, target} == {"sea_map", "glass_lens"}
    if map_and_lens:
        if "sea_map" not in inventory:
            return Event(
                type="use_failed",
                message_key="use_failed_missing_item",
                entities=("sea_map",),
                tags=("validation",),
                turn_index=turn_index,
            )
        if "glass_lens" not in inventory:
            return Event(
                type="use_failed",
                message_key="use_failed_missing_item",
                entities=("glass_lens",),
                tags=("validation",),
                turn_index=turn_index,
            )
        if state.player.flags.get("relay_route_confirmed", False):
            return _use_event(
                turn_index,
                target_label,
                "The lens confirms your marked routes still converge on the sanctuary.",
            )
        state.player.flags["relay_route_confirmed"] = True
        return _use_event(
            turn_index,
            target_label,
            "You map the relay route: archive vault, tower stair, then sanctuary.",
            delta_progress=0.08,
        )

    if item_id == "ropes" and target in {"bell", "bell_frame", "frame"}:
        if location != "tower_top":
            return Event(
                type="use_failed",
                message_key="You need to brace the frame from the tower top.",
                entities=target_label,
                tags=("validation",),
                turn_index=turn_index,
            )
        if "bell_pin" not in inventory:
            return Event(
                type="use_failed",
                message_key="The rope slips free without the bell pin.",
                entities=("bell_pin",),
                tags=("validation",),
                turn_index=turn_index,
            )
        if state.player.flags.get("frame_braced", False):
            return _use_event(
                turn_index,
                target_label,
                "The frame is already braced and steady in the wind.",
            )
        state.player.flags["frame_braced"] = True
        return _use_event(
            turn_index,
            target_label,
            "You brace the shattered bell frame. The resonance stabilizes toward the sanctuary.",
            delta_progress=0.1,
        )

    if item_id == "moonstone" and location == "sanctuary":
        if not state.player.flags.get("frame_braced", False):
            return Event(
                type="use_failed",
                message_key="The tone scatters until the tower frame is braced.",
                entities=target_label,
                tags=("validation",),
                turn_index=turn_index,
            )
        if state.player.flags.get("transmitter_exposed", False):
            return _use_event(
                turn_index,
                target_label,
                "The moonstone keeps the hidden resonator exposed.",
            )
        state.player.flags["transmitter_exposed"] = True
        return _use_event(
            turn_index,
            target_label,
            "The moonstone reveals a hidden resonator beneath the altar.",
            delta_progress=0.16,
        )

    return _use_event(turn_index, target_label, "use_success")


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
                message_key=take_item_message(item),
                entities=(action.target,),
                delta_progress=item.delta_progress,
                delta_tension=0.02,
                tags=("world", "quest_item" if "quest" in item.tags else "world_item"),
                turn_index=next_state.turn_index,
                metadata={"item_kind": item.kind, "item_name": item.name},
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
                },
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

        events.append(_resolve_use(next_state, item_id, target))
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
