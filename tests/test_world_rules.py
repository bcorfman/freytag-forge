from random import Random

from storygame.engine.parser import parse_command
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
