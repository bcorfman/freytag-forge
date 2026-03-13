from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.world import build_default_state
from storygame.llm.adapters import MockNarrator
from storygame.llm.context import build_narration_context
from storygame.llm.prompts import build_prompt


def test_mock_narrator_snapshot_output():
    state = build_default_state(seed=7)
    rng = Random(7)
    state, _events, beat, _template = advance_turn(state, parse_command("look"), rng)
    action = parse_command("look")
    context = build_narration_context(state, action, beat)
    narrator = MockNarrator(prefix="DBG:")
    result = narrator.generate(context)
    assert result.startswith("DBG:")
    assert "beat at" in result


def test_mock_narrator_supports_memory_fragments():
    state = build_default_state(seed=1)
    rng = Random(1)
    state, _events, beat, _template = advance_turn(state, parse_command("talk guide"), rng)
    context = build_narration_context(
        state,
        parse_command("look"),
        beat,
        memory_fragments=("Prior note: guide trusts your request.",),
    )
    result = MockNarrator().generate(context)
    assert isinstance(result, str)
    assert "beat at" in result


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
    assert "room name" in system_text
    assert "room description" in system_text
    assert "items naturally" in system_text
    assert "exits" in system_text
    assert "npc interactions or background events" in system_text
    assert "do not reveal later twists early" in system_text
