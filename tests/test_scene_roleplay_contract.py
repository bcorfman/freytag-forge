"""Concept-level checks for the completed Markdown scene-roleplay contract."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from storygame.runtime.engine import SCENE_ENTRY_REQUEST, RuntimeEngine
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


def _selection_provider(state: RuntimeState, calls: list[str]) -> Callable[[str], object]:
    def provider(player_input: str) -> object:
        calls.append(player_input)
        assert state.current_scene_id == "1A"
        return {
            "segments": [{"kind": "narration", "text": "The current scene gains a concrete lead."}],
            "selected_knowledge_ids": ["k_sl_1a_b_r1"],
        }

    return provider


@pytest.mark.parametrize("player_input", POLICY_INPUTS)
def test_every_policy_style_reaches_the_provider_unchanged(player_input: str) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    calls: list[str] = []
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(state, _selection_provider(state, calls))

    engine.turn(player_input)

    assert calls == [player_input]
    assert "SL-1A-B" in state.fired_event_ids


def test_route_package_has_the_fixed_canonical_scene_chain() -> None:
    assert PACKAGE.storylet_routes.canonical_scene_chain == ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def test_storylet_event_cannot_be_reused_after_acceptance() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    knowledge_id = "k_sl_1a_b_r2"
    event_payload = {
        "segments": [{"kind": "narration", "text": "A bounded scene situation changes the pressure."}],
        "selected_knowledge_ids": [knowledge_id],
    }

    RuntimeEngine(state, lambda _: event_payload).turn("I recover Michelle's damaged recording.")

    assert "SL-1A-B" in state.fired_event_ids
    with pytest.raises(ProposalValidationError, match="not eligible"):
        RuntimeEngine(state, lambda _: event_payload).turn("I try to repeat it.")


def test_declared_pressure_event_advances_facts_without_parsing_waiting() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "I wait."}]})

    engine.turn("I wait.")
    engine.turn("I continue waiting.")

    assert state.facts.has("patrol_return_pressure", "story", value="true")
    assert "pressure_1a" in state.fired_event_ids
    assert state.facts.has("story_elapsed_seconds", "story", value="120")


def test_scene_opening_is_provider_authored_and_commits_no_canon() -> None:
    """The runtime must never author scene prose of its own."""

    state = RuntimeState.bootstrap(PACKAGE)
    before = state.snapshot()
    requests: list[str] = []

    def provider(player_input: str) -> object:
        requests.append(player_input)
        return {"segments": [{"kind": "narration", "text": "Kristin steps into a house that answers nothing."}]}

    opening = RuntimeEngine(state, provider).opening()

    assert requests == [SCENE_ENTRY_REQUEST]
    assert opening.narration == "Kristin steps into a house that answers nothing."
    assert state.snapshot() == before


def test_scene_opening_prefers_a_provider_that_narrates_scene_entry_itself() -> None:
    state = RuntimeState.bootstrap(PACKAGE)

    class _OpeningProvider:
        def opening(self) -> object:
            return {"segments": [{"kind": "narration", "text": "The kitchen light is still on."}]}

        def __call__(self, player_input: str) -> object:
            raise AssertionError("an opening must not be requested as an ordinary turn")

    opening = RuntimeEngine(state, _OpeningProvider()).opening()

    assert opening.narration == "The kitchen light is still on."
    assert opening.selected_knowledge_ids == ()
