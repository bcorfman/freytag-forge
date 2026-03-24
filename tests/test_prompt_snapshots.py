from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.state import Event
from storygame.engine.simulation import advance_turn
from storygame.engine.world import build_default_state
from storygame.llm.context import build_narration_context
from storygame.llm.prompts import build_prompt
from tests.narrator_stubs import StubNarrator


def test_stub_narrator_returns_text():
    state = build_default_state(seed=7)
    rng = Random(7)
    state, _events, beat, _template = advance_turn(state, parse_command("look"), rng)
    action = parse_command("look")
    context = build_narration_context(state, action, beat)
    narrator = StubNarrator("DBG:narration")
    result = narrator.generate(context)
    assert result.startswith("DBG:")
    assert "narration" in result


def test_stub_narrator_supports_memory_fragments():
    state = build_default_state(seed=1)
    rng = Random(1)
    state, _events, beat, _template = advance_turn(state, parse_command("talk guide"), rng)
    context = build_narration_context(
        state,
        parse_command("look"),
        beat,
        memory_fragments=("Prior note: guide trusts your request.",),
    )
    result = StubNarrator().generate(context)
    assert isinstance(result, str)
    assert result == ""


def test_prompt_includes_if_storytelling_quality_checklist():
    state = build_default_state(seed=2)
    rng = Random(2)
    state, _events, beat, _template = advance_turn(state, parse_command("look"), rng)
    context = build_narration_context(state, parse_command("look"), beat)

    prompt = build_prompt(context)
    system_text = prompt["system"].lower()

    assert "opening scene (turn 0 only)" in system_text
    assert "3-4 paragraphs" in system_text
    assert "who the player is" in system_text
    assert "where they are" in system_text
    assert "immediate objective" in system_text
    assert "use present tense" in system_text
    assert "materially consistent with the room description, exits, visible items, visible npcs, and inventory" in system_text
    assert "do not invent extra furniture, desks, tables, papers, or document staging" in system_text
    assert "room name" in system_text
    assert "room description" in system_text
    assert "items naturally" in system_text
    assert "exits" in system_text
    assert "npc interactions or background events" in system_text
    assert "do not reveal later twists early" in system_text


def test_prompt_user_payload_includes_room_grounding_fields():
    state = build_default_state(seed=5)
    rng = Random(5)
    state, _events, beat, _template = advance_turn(state, parse_command("look"), rng)
    context = build_narration_context(state, parse_command("look"), beat)

    prompt = build_prompt(context)
    user_text = prompt["user"]

    assert "Room description: " in user_text
    assert "Exits: " in user_text
    assert f"Location: {context.room_name}" in user_text
    assert f"Room description: {context.room_description}" in user_text
    assert "Scene facts: " in user_text
    assert "Visible item facts: " in user_text
    assert "Visible items: " in user_text
    assert "Visible NPCs: " in user_text
    assert "Inventory: " in user_text


def test_prompt_instructs_npc_reply_for_addressed_freeform_turns():
    state = build_default_state(seed=3, genre="mystery")
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

    prompt = build_prompt(context)

    assert "For conversational freeform turns with an addressed NPC" in prompt["system"]
    assert "prefer a direct in-world reply from that NPC" in prompt["system"]
    assert "Addressed NPC: Daria Stone" in prompt["user"]
    assert "Conversation topic: appearance" in prompt["user"]
