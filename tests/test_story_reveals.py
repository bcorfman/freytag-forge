from __future__ import annotations

from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.world import build_default_state


def test_story_reveal_emits_once_when_progress_threshold_is_met():
    state = build_default_state(seed=201, genre="mystery")
    state.world_package["story_plan"]["hidden_threads"] = ("The buried case file points to a missing witness.",)
    state.world_package["story_plan"]["reveal_schedule"] = ({"thread_index": 0, "min_progress": 0.0},)

    rng = Random(201)
    next_state, events, _beat, _template = advance_turn(state, parse_command("look"), rng)
    reveal_events = [event for event in events if event.type == "story_reveal"]
    assert len(reveal_events) == 1
    assert "missing witness" in reveal_events[0].message_key.lower()
    assert next_state.player.flags.get("story_reveal_0") is True

    later_state, later_events, _beat, _template = advance_turn(next_state, parse_command("look"), rng)
    assert not [event for event in later_events if event.type == "story_reveal"]
    assert later_state.player.flags.get("story_reveal_0") is True


def test_story_reveal_waits_until_threshold():
    state = build_default_state(seed=202, genre="mystery")
    state.world_package["story_plan"]["hidden_threads"] = ("A final ledger links the suspect to the magistrate.",)
    state.world_package["story_plan"]["reveal_schedule"] = ({"thread_index": 0, "min_progress": 0.95},)
    state.progress = 0.1

    rng = Random(202)
    _next_state, events, _beat, _template = advance_turn(state, parse_command("look"), rng)
    assert not [event for event in events if event.type == "story_reveal"]


def test_story_reveal_can_run_from_fact_backed_story_plan():
    state = build_default_state(seed=203, genre="mystery")
    state.world_package["story_plan"]["hidden_threads"] = ()
    state.world_package["story_plan"]["reveal_schedule"] = ()
    state.world_facts.assert_fact("story_hidden_thread", "The hidden ledger links the victim to the magistrate.")
    state.world_facts.assert_fact("story_reveal_schedule", "0", "0.0")

    rng = Random(203)
    next_state, events, _beat, _template = advance_turn(state, parse_command("look"), rng)

    reveal_events = [event for event in events if event.type == "story_reveal"]
    assert len(reveal_events) == 1
    assert "hidden ledger" in reveal_events[0].message_key.lower()
    assert next_state.player.flags.get("story_reveal_0") is True


def test_timed_story_event_preserves_fact_backed_participants():
    state = build_default_state(seed=204, genre="mystery")
    state.world_package["story_plan"]["timed_events"] = ()
    state.world_facts.assert_fact("planned_event", "warning", "Records are burning upstairs.", "0", "foyer")
    state.world_facts.assert_fact("planned_event_participant", "warning", "Daria Stone")

    rng = Random(204)
    _next_state, events, _beat, _template = advance_turn(state, parse_command("look"), rng)

    timed_events = [event for event in events if event.type == "timed_story_event"]
    assert len(timed_events) == 1
    assert timed_events[0].entities == ("Daria Stone",)
