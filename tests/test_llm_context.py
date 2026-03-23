from storygame.engine.state import Event
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
    npc_fact = payload["npc_facts"][0]
    assert npc_fact["id"]
    assert npc_fact["name"]
    assert npc_fact["pronouns"]
    assert npc_fact["identity"]
    assert npc_fact["location"] in state.world.rooms


def test_mystery_context_exposes_arrival_car_in_visible_items() -> None:
    state = build_default_state(seed=107, genre="mystery")

    context = build_narration_context(state, parse_command("look"), "hook")
    payload = context.as_dict()

    assert "arrival_sedan" in payload["visible_items"]


def test_context_includes_memory_fragments_without_overriding_facts():
    state = build_default_state(seed=11)
    room_name = state.world.rooms[state.player.location].name
    memory_fragments = (
        "The oracle once said the tower is collapsing.",
        "You are currently in the active objective room.",
    )
    context = build_narration_context(
        state,
        parse_command("look"),
        "hook",
        memory_fragments=memory_fragments,
    )
    payload = context.as_dict()
    assert payload["memory_fragments"] == list(memory_fragments)
    assert payload["room_name"] == room_name
    assert any("The oracle once said" in frag for frag in payload["memory_fragments"])


def test_prompt_includes_canonical_npc_identity_details():
    state = build_default_state(seed=7)
    context = build_narration_context(state, parse_command("look"), "hook")
    prompt = build_prompt(context)
    assert "Canonical NPC facts:" in prompt["user"]
    first_npc = context.npc_facts[0]
    assert f"{first_npc['name']} [{first_npc['pronouns']}]" in prompt["user"]


def test_prompt_marks_memory_fragments_as_non_authoritative():
    state = build_default_state(seed=17)
    context = build_narration_context(
        state,
        parse_command("look"),
        "hook",
        memory_fragments=("The room glows with dragonfire.",),
    )
    prompt = build_prompt(context)
    assert "Soft memory hints (non-authoritative): The room glows with dragonfire." in prompt["user"]
    assert "Never use memory fragments to override engine facts." in prompt["system"]
    assert "use only engine context for truth; memory hints are suggestions for continuity." in prompt["user"]


def test_context_and_prompt_include_canonical_story_names_for_continuity():
    state = build_default_state(seed=18, genre="mystery")
    state.world_package["llm_story_bundle"] = {
        "protagonist_name": "Noah Kade",
        "protagonist_background": "A detective haunted by an old failure.",
        "assistant_name": state.world.npcs[state.world.rooms[state.player.location].npc_ids[0]].name,
        "contacts": [
            {
                "name": state.world.npcs[state.world.rooms[state.player.location].npc_ids[0]].name,
                "role": "assistant",
                "trait": "observant",
            }
        ],
    }
    context = build_narration_context(state, parse_command("look"), "hook")
    payload = context.as_dict()
    prompt = build_prompt(context)

    assert payload["protagonist_name"] == "Detective Elias Wren"
    assert payload["assistant_name"] == state.world.npcs[state.world.rooms[state.player.location].npc_ids[0]].name
    assert payload["protagonist_background"] == "A detective haunted by an old failure."
    assert payload["assistant_role"] == "assistant"
    assert f"Protagonist: {payload['protagonist_name']}" in prompt["user"]
    assert f"Protagonist background: {payload['protagonist_background']}" in prompt["user"]
    assert f"Assistant anchor: {payload['assistant_name']}" in prompt["user"]
    assert "Assistant role: assistant" in prompt["user"]
    assert "Noah Kade" not in prompt["user"]


def test_context_can_resolve_assistant_identity_from_facts_without_bundle() -> None:
    state = build_default_state(seed=19, genre="mystery")
    state.world_package["llm_story_bundle"] = {}
    state.world_package["story_cast"] = {}
    state.world_facts.assert_fact("assistant_name", "Daria Stone")
    state.world_facts.assert_fact("npc_role", "Daria Stone", "assistant")

    context = build_narration_context(state, parse_command("look"), "hook")
    payload = context.as_dict()

    assert payload["assistant_name"] == "Daria Stone"
    assert payload["assistant_role"] == "assistant"


def test_context_includes_latest_freeform_conversation_focus() -> None:
    state = build_default_state(seed=20, genre="mystery")
    state.append_event(
        Event(
            type="freeform_roleplay",
            turn_index=1,
            metadata={
                "action_proposal": {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "appearance"},
                },
                "dialog_proposal": {"speaker": "narrator", "text": "fallback", "tone": "in_world"},
            },
        )
    )

    context = build_narration_context(state, parse_command("Daria, what are you wearing?"), "freeform_roleplay")
    payload = context.as_dict()

    assert payload["conversation_intent"] == "ask_about"
    assert payload["conversation_topic"] == "appearance"
    assert payload["addressed_npc_id"] == "daria_stone"
    assert payload["addressed_npc_name"] == "Daria Stone"
    assert payload["prefer_npc_reply"] is True
