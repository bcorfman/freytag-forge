"""Phase 4 progression contracts remain generic across story genres."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.authoring.contracts import CompiledStory
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import bootstrap_runtime_state


class _Model:
    def play_turn(self, context: object, *, json_object: bool) -> object:
        return {"narration": "The pressure rises, but a new option appears.", "operations": []}


def _progression_story(genre: str) -> CompiledStory:
    story = load_compiled_story_fixture(genre)
    return CompiledStory.model_validate(
        story.model_dump(mode="json")
        | {
            "scene_purpose": "Make a consequential choice.",
            "dramatic_question": "What will the player risk?",
            "initial_pressure": 20,
            "goals": [{"id": "survive", "summary": "Reach a viable outcome."}],
            "tasks": [{"id": "choose", "goal_id": "survive", "summary": "Choose a path", "initial_status": "active"}],
            "clues": [{"id": "signal", "summary": "A useful signal", "fact_ids": ["signal_found"]}],
            "relationships": [{"subject_id": "player", "target_id": story.characters[0].id, "relationship": "ally"}],
            "timed_events": [
                {
                    "id": "clock_ticks",
                    "after_turn": 1,
                    "pressure_change": 10,
                    "consequence_facts": [{"predicate": "flag", "subject": "world", "object": "clock_ticked"}],
                }
            ],
            "endings": [{"id": "viable", "summary": "A viable future remains.", "failure_forward": True}],
        }
    )


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "relationship"))
def test_progression_metadata_bootstraps_as_facts_and_context(genre: str) -> None:
    state = bootstrap_runtime_state(_progression_story(genre))
    assert state.facts.matching("goal", "player")
    assert state.facts.has("task", "player", "choose", "active")
    assert state.facts.matching("clue", "signal")
    assert state.facts.has("dramatic_question", "scene", value="What will the player risk?")
    assert state.facts.has("scene_pressure", "scene", value="20")


def test_timed_event_commits_once_and_updates_pressure() -> None:
    state = bootstrap_runtime_state(_progression_story("mystery"))
    engine = RuntimeEngine(state, _Model())
    assert engine.turn("Wait and watch.").ok
    assert engine.state.facts.has("flag", "world", "clock_ticked")
    assert engine.state.facts.matching("event_fired", "clock_ticks")
    assert engine.state.facts.has("scene_pressure", "scene", value="30")
    assert len(engine.state.facts.matching("event_fired", "clock_ticks")) == 1


def test_invalid_progression_references_fail_at_authoring_boundary() -> None:
    story = load_compiled_story_fixture("fantasy")
    with pytest.raises((ValidationError, ValueError)):
        CompiledStory.model_validate(
            story.model_dump(mode="json") | {"tasks": [{"id": "lost", "goal_id": "missing", "summary": "No goal"}]}
        )
