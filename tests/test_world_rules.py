from random import Random

from storygame.engine.parser import Action, ActionKind, parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state


def test_move_locked_exit_requires_key():
    state = build_default_state(seed=1)
    to_market = apply_action(state, parse_command("north"), Random(1))[0]
    to_archives = apply_action(to_market, parse_command("east"), Random(1))[0]
    locked_result, locked_events = apply_action(
        to_archives,
        parse_command("north"),
        Random(1),
    )
    assert locked_result.player.location == "archives"
    assert any(event.type == "move_failed" for event in locked_events)


def test_use_requires_inventory_item():
    state = build_default_state(seed=1)
    to_market = apply_action(state, parse_command("north"), Random(1))[0]
    with_key_in_room = apply_action(to_market, parse_command("look"), Random(1))[0]
    _, use_events = apply_action(
        with_key_in_room,
        parse_command("use bronze key on gate"),
        Random(1),
    )
    assert any(event.type == "use_failed" for event in use_events)


def test_move_after_finding_key_and_take():
    state = build_default_state(seed=1)
    to_market = apply_action(state, parse_command("north"), Random(1))[0]
    with_key_state, key_events = apply_action(
        to_market,
        parse_command("take bronze key"),
        Random(1),
    )
    assert "bronze_key" in with_key_state.player.inventory
    assert any(event.type == "take" for event in key_events)

    to_archives = apply_action(with_key_state, parse_command("east"), Random(1))[0]
    inner_archive, events_inner = apply_action(
        to_archives,
        parse_command("north"),
        Random(1),
    )
    assert inner_archive.player.location == "inner_archive"
    assert any(event.type == "move" for event in events_inner)


def test_take_missing_item_and_talk_missing_npc_fail():
    state = build_default_state(seed=2)
    _, take_events = apply_action(
        state,
        parse_command("take moonstone"),
        Random(2),
    )
    assert any(event.type == "take_failed" for event in take_events)

    _, talk_events = apply_action(
        state,
        parse_command("talk stranger"),
        Random(2),
    )
    assert any(event.type == "talk_failed" for event in talk_events)


def test_move_by_room_name_target_uses_exit_values():
    state = build_default_state(seed=4)
    moved_state, events = apply_action(
        state,
        Action(ActionKind.MOVE, target="market"),
        Random(4),
    )
    assert moved_state.player.location == "market"
    assert any(event.type == "move" for event in events)


def test_take_non_portable_item_fails():
    state = build_default_state(seed=5)
    to_market = apply_action(state, parse_command("north"), Random(5))[0]
    to_market.world.items["bronze_key"].portable = False

    _, take_events = apply_action(
        to_market,
        parse_command("take bronze key"),
        Random(5),
    )
    assert any(event.type == "take_failed" for event in take_events)
    assert not any(event.type == "take" for event in take_events)


def test_talk_previous_and_unknown_action_events():
    state = build_default_state(seed=3)
    to_market = apply_action(state, parse_command("north"), Random(3))[0]
    to_archives = apply_action(to_market, parse_command("east"), Random(3))[0]
    after_talk, first_talk_events = apply_action(
        to_archives,
        parse_command("talk keeper"),
        Random(3),
    )
    _, second_talk_events = apply_action(
        after_talk,
        parse_command("talk keeper"),
        Random(3),
    )

    assert any(event.type == "talk" for event in first_talk_events)
    assert any(event.type == "talk" for event in second_talk_events)
    assert any(event.delta_progress == 0.0 for event in second_talk_events)

    _, unknown_events = apply_action(
        to_archives,
        Action(ActionKind.UNKNOWN, raw="do nonsense"),
        Random(3),
    )
    assert any(event.type == "unknown" for event in unknown_events)


def test_use_map_and_lens_supports_first_and_repeat_route_mapping():
    state = build_default_state(seed=11)
    state.player.inventory = ("sea_map", "glass_lens")

    first, first_events = apply_action(
        state,
        Action(ActionKind.USE, target="sea_map:glass_lens"),
        Random(11),
    )
    assert first_events[0].message_key == "You map the relay route: archive vault, tower stair, then sanctuary."
    assert first.player.flags["relay_route_confirmed"] is True

    second, second_events = apply_action(
        first,
        Action(ActionKind.USE, target="sea_map:glass_lens"),
        Random(11),
    )
    assert any("still converge on the sanctuary" in event.message_key for event in second_events)


def test_use_rope_requires_tower_top_and_bell_pin_then_braces_frame():
    state = build_default_state(seed=11)
    state.player.inventory = ("ropes",)

    first, first_events = apply_action(
        state,
        Action(ActionKind.USE, target="ropes:frame"),
        Random(11),
    )
    assert any(event.type == "use_failed" for event in first_events)

    state.player.location = "tower_top"
    state.player.inventory = ("ropes", "bell_pin")
    second, second_events = apply_action(
        state,
        Action(ActionKind.USE, target="ropes:frame"),
        Random(11),
    )
    assert any("brace the shattered bell frame" in event.message_key.lower() for event in second_events)
    assert second.player.flags["frame_braced"] is True


def test_use_moonstone_requires_braced_frame_then_exposes_resonator():
    state = build_default_state(seed=11)
    state.player.location = "sanctuary"
    state.player.inventory = ("moonstone",)

    first, first_events = apply_action(
        state,
        Action(ActionKind.USE, target="moonstone:altar"),
        Random(11),
    )
    assert any("scatters until" in event.message_key for event in first_events)

    state.player.flags["frame_braced"] = True
    second, second_events = apply_action(
        state,
        Action(ActionKind.USE, target="moonstone:altar"),
        Random(11),
    )
    assert any("hidden resonator" in event.message_key.lower() for event in second_events)
    assert second.player.flags["transmitter_exposed"] is True


def test_use_unhandled_item_falls_back_to_success_message():
    state = build_default_state(seed=11)
    state.player.inventory = ("glass_lens",)

    _, events = apply_action(
        state,
        Action(ActionKind.USE, target="glass_lens:bell"),
        Random(11),
    )
    assert any(event.message_key == "use_success" for event in events)
