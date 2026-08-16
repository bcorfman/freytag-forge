from storygame.engine.facts import active_story_goal, apply_fact_ops, player_location
from storygame.engine.parser import Action, ActionKind
from storygame.engine.rules import apply_action
from storygame.persistence.savegame_sqlite import serialize_state
from tests.fast_fixtures import make_cached_story_state as build_default_state


def test_ordinary_action_does_not_rebuild_facts_from_stale_projection() -> None:
    state = build_default_state(seed=41)
    apply_fact_ops(state, [{"op": "assert", "fact": ("at", "player", "tower")}])
    state.player.location = "old_room"

    next_state, _ = apply_action(state, Action(kind=ActionKind.LOOK, raw="look"), None)

    assert player_location(next_state) == "tower"
    assert next_state.player.location == "old_room"


def test_active_goal_has_no_projection_fallback() -> None:
    state = build_default_state(seed=42)
    state.world_facts.retract_fact("active_goal", state.active_goal)
    state.active_goal = "stale projection"

    assert active_story_goal(state) == ""


def test_serialization_refreshes_projection_from_facts_without_rebuilding_them() -> None:
    state = build_default_state(seed=43)
    apply_fact_ops(state, [{"op": "assert", "fact": ("at", "player", "tower")}])
    state.player.location = "old_room"

    payload = serialize_state(state)

    assert payload["player"]["location"] == "tower"
    assert ["at", "player", "tower"] in payload["world_facts"]
    assert ["at", "player", "old_room"] not in payload["world_facts"]


def test_event_template_flags_are_committed_as_facts() -> None:
    from storygame.engine.events import EventTemplate, apply_event_template

    state = build_default_state(seed=44)
    template = EventTemplate(key="test", message_key="test", tags=(), set_flags=("committed",))

    next_state, events = apply_event_template(state, template, None)

    assert next_state.world_facts.holds("flag", "player", "committed")
    assert next_state.player.flags["committed"] is True
    assert events[0].metadata["fact_ops"] == [{"op": "assert", "fact": ("flag", "player", "committed")}]
