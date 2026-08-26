"""Concept-level checks for the completed Markdown scene-roleplay contract."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
POLICY_INPUTS = (
    "I pursue the immediate objective decisively.",
    "I investigate every useful clue before I act.",
    "I ask for help and make a shared plan.",
    "I take the safest legal route forward.",
    "I confront the obstacle without destroying a required dependency.",
    "I improvise a strange but legal way to advance the current scene.",
)


def _transition_provider(state: RuntimeState, calls: list[str]) -> Callable[[str], object]:
    transitions = {transition.source_scene_id: transition for transition in PACKAGE.pacing.transitions}

    def provider(player_input: str) -> object:
        calls.append(player_input)
        transition = transitions[state.current_scene_id]
        operations = [
            {
                "operation": "assert",
                "fact": {"predicate": trigger.fact_id, "subject": "story", "value": str(trigger.equals).lower()},
            }
            for trigger in transition.triggers
        ]
        return {
            "narration": "The current scene moves forward through the validated proposal.",
            "operations": operations,
            "transition": {"transition_id": transition.id},
        }

    return provider


@pytest.mark.parametrize("player_input", POLICY_INPUTS)
def test_every_policy_style_reaches_the_provider_unchanged(player_input: str) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    calls: list[str] = []
    engine = RuntimeEngine(state, _transition_provider(state, calls))

    engine.turn(player_input)

    assert calls == [player_input]
    assert state.current_scene_id == "1B"


def test_declared_transition_graph_reaches_climax_with_validated_facts() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    calls: list[str] = []
    engine = RuntimeEngine(state, _transition_provider(state, calls))

    for _ in PACKAGE.pacing.transitions:
        engine.turn("I follow the current objective.")

    assert state.current_scene_id == "3C"
    assert len(calls) == len(PACKAGE.pacing.transitions)
    assert state.facts.has("broadcast_started", "story", value="true")


def test_storylet_event_cannot_be_reused_after_acceptance() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    first = RuntimeEngine(state, lambda _: {"narration": "I search the room."})
    first.turn("I examine the room.")
    storylet_id = next(iter(state.active_event_ids))
    event_payload = {
        "narration": "A bounded scene situation changes the pressure.",
        "events": [{"event_id": storylet_id, "operations": []}],
    }

    RuntimeEngine(state, lambda _: event_payload).turn("I follow the lead.")

    assert storylet_id in state.fired_event_ids
    with pytest.raises(ProposalValidationError, match="not active"):
        RuntimeEngine(state, lambda _: event_payload).turn("I try to repeat it.")


def test_declared_pressure_event_advances_facts_without_parsing_waiting() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, lambda _: {"narration": "I wait.", "narrative_seconds": 60})

    engine.turn("I wait.")
    engine.turn("I continue waiting.")

    assert state.facts.has("facility_proof", "story", value="true")
    assert "pressure_1a" in state.fired_event_ids
    assert state.facts.has("story_elapsed_seconds", "story", value="120")
