from __future__ import annotations

from random import Random

from storygame.engine.events import EventTemplate, apply_event_template, select_event
from storygame.engine.world import build_default_state
from storygame.plot.beat_manager import Beat


def test_select_event_falls_back_to_full_template_library_when_tags_do_not_match() -> None:
    state = build_default_state(seed=601)
    beat = Beat(type="custom", tags=("unknown_tag",))
    template = select_event(beat, state, Random(6))
    assert isinstance(template.key, str)
    assert template.key


def test_apply_event_template_sets_and_clears_flags() -> None:
    state = build_default_state(seed=602)
    state.player.flags["already_set"] = True
    template = EventTemplate(
        key="x",
        message_key="m",
        tags=("hook",),
        set_flags=("new_flag",),
        clear_flags=("already_set",),
    )
    next_state, events = apply_event_template(state, template, Random(6))
    assert next_state.player.flags["new_flag"] is True
    assert next_state.player.flags["already_set"] is False
    assert events[0].type == "plot"
