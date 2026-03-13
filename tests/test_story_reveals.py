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
