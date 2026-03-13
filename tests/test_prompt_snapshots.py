from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.world import build_default_state
from storygame.llm.adapters import MockNarrator
from storygame.llm.context import build_narration_context


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
