from __future__ import annotations

from random import Random

from storygame.cli import run_turn
from storygame.engine.events import list_event_templates
from storygame.engine.parser import parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state
from storygame.llm.adapters import SilentNarrator


def _event_texts() -> tuple[str, ...]:
    return tuple(template.message_key.lower() for template in list_event_templates())


def test_plot_templates_avoid_broken_bell_and_memory_trap_contradictions():
    texts = _event_texts()
    assert not any("memory trap" in text for text in texts)
    assert not any("warning bell clangs" in text for text in texts)
    assert not any("bell speaks" in text for text in texts)


def test_room_output_includes_signal_direction_hint():
    state = build_default_state(seed=11)
    rng = Random(11)

    next_state, lines, *_ = run_turn(state, "look", rng, SilentNarrator())

    assert next_state.player.location == "harbor"
    assert any("Signal:" in line for line in lines)


def test_npc_dialogue_is_actionable_and_exposed_in_talk_event_text():
    state = build_default_state(seed=12)
    rng = Random(12)

    state = apply_action(state, parse_command("north"), rng)[0]
    state = apply_action(state, parse_command("east"), rng)[0]

    next_state, events = apply_action(state, parse_command("talk keeper"), rng)

    assert next_state.player.flags.get("talked_keeper") is True
    talk_events = [event for event in events if event.type == "talk"]
    assert talk_events
    assert "bronze key" in talk_events[0].message_key.lower()
    assert "north gate" in talk_events[0].message_key.lower()


def test_useful_item_pair_advances_progress_and_sets_flag():
    state = build_default_state(seed=13)
    rng = Random(13)

    state = apply_action(state, parse_command("take sea map"), rng)[0]
    state = apply_action(state, parse_command("north"), rng)[0]
    state = apply_action(state, parse_command("take glass lens"), rng)[0]

    next_state, events = apply_action(state, parse_command("use glass lens on sea map"), rng)

    use_events = [event for event in events if event.type == "use"]
    assert use_events
    assert use_events[0].delta_progress > 0.0
    assert next_state.player.flags.get("relay_route_confirmed") is True


def test_story_goal_is_specific_and_not_just_follow_bell_signal():
    state = build_default_state(seed=14)

    goal = state.active_goal.lower()
    assert "bell signal" not in goal
    assert "conspiracy" in goal
    assert "relay" in goal
