from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.world import build_default_state
from storygame.llm.context import MAX_RECENT_EVENTS, build_narration_context
from storygame.llm.prompts import build_prompt


def test_context_includes_required_fields_and_limits():
    state = build_default_state(seed=99)
    rng = Random(99)
    action = parse_command("go north")
    state, events, beat_type, _template = advance_turn(state, action, rng)
    assert len(state.event_log) == 2

    for _ in range(MAX_RECENT_EVENTS + 2):
        state, _events, _beat, _template = advance_turn(state, parse_command("look"), rng)

    context = build_narration_context(state, parse_command("look"), beat_type)
    payload = context.as_dict()

    assert payload["room_name"]
    assert payload["visible_items"] is not None
    assert payload["phase"]
    assert payload["beat"]
    assert payload["goal"]
    assert len(payload["recent_events"]) <= MAX_RECENT_EVENTS
    assert payload["npc_facts"]
    keeper = next((fact for fact in payload["npc_facts"] if fact["id"] == "keeper"), None)
    assert keeper is not None
    assert keeper["pronouns"] == "she/her"
    assert "female archivist" in keeper["identity"]


def test_prompt_includes_canonical_npc_identity_details():
    state = build_default_state(seed=7)
    context = build_narration_context(state, parse_command("look"), "hook")
    prompt = build_prompt(context)
    assert "Canonical NPC facts:" in prompt["user"]
    assert "High Oracle [she/her]" in prompt["user"]
