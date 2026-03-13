from __future__ import annotations

from random import Random

from storygame.cli import run_turn
from storygame.engine.events import list_event_templates
from storygame.engine.parser import parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state
from storygame.llm.adapters import SilentNarrator
from tests.narrator_stubs import StubNarrator


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
    start_room = state.player.location

    next_state, lines, *_ = run_turn(state, "look", rng, SilentNarrator())

    assert next_state.player.location == start_room
    assert any("exit" in line.lower() for line in lines)


def test_npc_dialogue_is_actionable_and_exposed_in_talk_event_text():
    state = build_default_state(seed=12)
    rng = Random(12)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    next_state, events = apply_action(state, parse_command(f"talk {npc_id}"), rng)

    assert next_state.player.flags.get(f"talked_{npc_id}") is True
    talk_events = [event for event in events if event.type == "talk"]
    assert talk_events
    assert talk_events[0].message_key


def test_use_event_emits_when_inventory_item_is_available():
    state = build_default_state(seed=13)
    rng = Random(13)
    item_id = next(iter(state.world.items.keys()))
    state.player.inventory = (item_id,)
    state.world_facts.assert_fact("holding", "player", item_id)

    next_state, events = apply_action(state, parse_command(f"use {item_id} on target"), rng)

    use_events = [event for event in events if event.type == "use"]
    assert use_events
    assert use_events[0].message_key == "use_success"
    assert next_state.turn_index == 1


def test_story_goal_is_specific_and_not_just_follow_bell_signal():
    state = build_default_state(seed=14, genre="thriller")

    goal = state.active_goal.lower()
    assert "bell signal" not in goal
    assert "get oriented" in goal
    assert len(goal) > 40


def test_npcs_do_not_follow_player_between_rooms_without_trigger():
    state = build_default_state(seed=19)
    rng = Random(19)
    first_npc = state.world.rooms[state.player.location].npc_ids[0].replace("_", " ")
    direction = sorted(state.world.rooms[state.player.location].exits.keys())[0]
    destination = state.world.rooms[state.player.location].exits[direction]

    moved_state, lines, *_ = run_turn(state, direction, rng, StubNarrator(), debug=False)

    assert moved_state.player.location == destination
    combined = "\n".join(lines).lower()
    assert f"{first_npc} is here" not in combined
