from __future__ import annotations

from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.rules import _resolve_use, apply_action
from storygame.engine.state import Item
from storygame.engine.world import build_default_state


def test_resolve_use_returns_idempotent_event_when_flag_already_set() -> None:
    state = build_default_state(seed=621)
    state.turn_index = 3
    state.world_facts.assert_fact("flag", "player", "used_field_kit_self")
    event = _resolve_use(state, "field_kit", "")
    assert event.message_key == "use_success"
    assert event.delta_progress == 0.0


def test_apply_action_covers_help_take_not_portable_use_missing_and_unknown() -> None:
    state = build_default_state(seed=622)
    rng = Random(622)

    _state, events = apply_action(state, parse_command("help"), rng)
    assert events[0].type == "help"

    room = state.world.rooms[state.player.location]
    non_portable = "heavy_crate"
    state.world.items[non_portable] = Item(
        id=non_portable,
        name="Heavy Crate",
        description="Too heavy to carry.",
        portable=False,
    )
    room.item_ids = room.item_ids + (non_portable,)
    _state, events = apply_action(state, parse_command(f"take {non_portable}"), rng)
    assert events[0].message_key == "take_failed_not_portable"

    _state, events = apply_action(state, parse_command("use missing_item"), rng)
    assert events[0].message_key == "use_failed_missing_item"

    _state, events = apply_action(state, parse_command("completely unknown command"), rng)
    assert events[0].message_key == "unknown_command"
