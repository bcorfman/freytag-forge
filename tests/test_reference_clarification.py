from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.contracts import GameBreakWarning, ResolvedTurnProposal
from storygame.runtime.engine import ClarificationTurn, RuntimeEngine, StoryCompleteTurn
from storygame.runtime.state import RuntimeState, RuntimeStateError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state(scene_id: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    advance_state_to_scene(PACKAGE, state, scene_id)
    return state


def _provider(calls: list[str]):
    def provider(command: str):
        calls.append(command)
        return {"segments": [{"kind": "narration", "text": "The scene continues."}]}

    return provider


def test_unique_resolution_reaches_provider_without_rewriting_the_command() -> None:
    state = _state("1A")
    calls: list[str] = []
    engine = RuntimeEngine(state, _provider(calls))

    result = engine.turn("Search the chair.")

    assert result.selected_knowledge_ids == ()
    assert calls == ["Search the chair."]
    assert engine.last_reference_resolution is not None
    assert engine.last_reference_resolution.command == "Search the chair."


def test_answer_splices_only_the_ambiguous_noun() -> None:
    state = _state("2B")
    calls: list[str] = []
    engine = RuntimeEngine(state, _provider(calls))
    command = "Read the card and the terminal."

    question = engine.turn(command)
    result = engine.turn("medical", clarifies=command, clarification_round=0)

    assert isinstance(question, ClarificationTurn)
    assert question.clarification.noun == "terminal"
    assert result.narration == "The scene continues."
    assert calls == ["Read the card and the medical terminal."]
    assert engine.last_reference_resolution is not None
    assert engine.last_reference_resolution.resolutions == (
        ("terminal", "medical_terminal"),
        ("card", "memory_card"),
    )


@pytest.mark.nightly
def test_story_complete_and_pending_break_skip_resolution() -> None:
    complete_state = _state("2B")
    complete_state.story_complete = True
    complete_calls: list[str] = []
    complete_engine = RuntimeEngine(complete_state, _provider(complete_calls))

    complete = complete_engine.turn("Read the terminal.")

    assert isinstance(complete, StoryCompleteTurn)
    assert complete_calls == []
    assert complete_engine.last_reference_resolution is None

    break_state = _state("2B")
    break_state.set_pending_break(
        GameBreakWarning(
            warning_id="test_break",
            reason="test",
            snapshot_id="test_snapshot",
        ),
        snapshot=break_state.snapshot(),
        proposal=ResolvedTurnProposal(segments=({"kind": "narration", "text": "Candidate."},)),
    )
    break_calls: list[str] = []
    break_engine = RuntimeEngine(break_state, _provider(break_calls))

    with pytest.raises(RuntimeStateError):
        break_engine.turn("Read the terminal.")
    assert break_calls == []
    assert break_engine.last_reference_resolution is None
