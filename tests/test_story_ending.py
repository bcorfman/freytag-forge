"""Hermetic coverage for the package-declared story ending."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from storygame.runtime.engine import RuntimeEngine, StoryCompleteTurn
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.story_package.loader import StoryPackageError, _validate_ending, load_story_package
from storygame.story_package.models import FactPredicate, StoryEnding
from storygame.web_demo import _state_summary, _turn_payload

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def ending_package(**updates):
    ending = StoryEnding(
        scene_id="3C",
        when=(FactPredicate(fact_id="phase_two_conflict_plan_known", equals=True),),
        text="Test closing paragraph.",
        marker="The story ends here.",
    )
    ending = ending.model_copy(update=updates)
    return PACKAGE.model_copy(update={"pacing": PACKAGE.pacing.model_copy(update={"ending": ending})})


def state_for(package):
    state = RuntimeState(package=package, current_scene_id="3C", phase="resolution")
    state._assert_scene_entry_fact("3C")
    return state


def test_ending_fires_once_as_last_segment_and_later_turn_is_provider_free():
    package = ending_package()
    state = state_for(package)
    state.facts.assert_fact(Fact(predicate="phase_two_conflict_plan_known", subject="story", value="true"))
    calls = []

    def provider(_command):
        calls.append(True)
        return {"segments": [{"kind": "narration", "text": "The plan is clear."}]}

    engine = RuntimeEngine(state, provider)
    result = engine.turn("Wait.")
    assert result.segments[-1].text == "Test closing paragraph."
    assert state.story_complete is True
    assert engine.last_attempt.story_complete is True
    turn_index = state.turn_index
    result = engine.turn("Wait again.")
    assert isinstance(result, StoryCompleteTurn)
    assert result.narration == "The story ends here."
    assert state.turn_index == turn_index
    assert len(calls) == 1


def test_ending_requires_scene_and_predicate_and_snapshot_round_trips():
    package = ending_package()
    state = state_for(package)
    engine = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "Not yet."}]})
    result = engine.turn("Wait.")
    assert result.segments[-1].text == "Not yet."
    assert state.story_complete is False
    state.facts.assert_fact(Fact(predicate="phase_two_conflict_plan_known", subject="story", value="true"))
    state.story_complete = True
    restored = RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json())
    other = state_for(package)
    other.restore_snapshot(restored)
    assert other.story_complete is True
    old = restored.model_dump(mode="json")
    old.pop("story_complete")
    assert RuntimeSnapshot.model_validate(old).story_complete is False


def test_package_without_ending_is_unchanged():
    state = state_for(PACKAGE)
    engine = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "Continue."}]})
    result = engine.turn("Wait.")
    assert result.segments[-1].text == "Continue."
    assert state.story_complete is False


def test_loader_accepts_protected_terms_in_authored_ending():
    _validate_ending(ending_package(text="Phase Two was stopped.", marker="Phase Two is over."))


@pytest.mark.parametrize(
    ("ending", "message"),
    [
        (
            StoryEnding(
                scene_id="9Z",
                when=(FactPredicate(fact_id="phase_two_conflict_plan_known"),),
                text="x",
                marker="m",
            ),
            "unknown scene",
        ),
        (
            StoryEnding(scene_id="3C", when=(FactPredicate(fact_id="not_a_fact"),), text="x", marker="m"),
            "unknown predicate",
        ),
        (
            StoryEnding(
                scene_id="3C",
                when=(FactPredicate(fact_id="phase_two_conflict_plan_known"),),
                text="x",
                marker="m",
            ),
            "outgoing transition",
        ),
    ],
)
def test_loader_rejects_invalid_ending_references(ending, message):
    transitions = PACKAGE.pacing.transitions
    if message == "outgoing transition":
        transitions = transitions + (transitions[0].model_copy(update={"source_scene_id": "3C"}),)
    package = PACKAGE.model_copy(
        update={"pacing": PACKAGE.pacing.model_copy(update={"ending": ending, "transitions": transitions})}
    )
    with pytest.raises(StoryPackageError, match=message):
        _validate_ending(package)


def test_ending_model_rejects_blank_text_and_old_attempt_bundles_load():
    with pytest.raises(ValidationError):
        StoryEnding(scene_id="3C", when=(FactPredicate(fact_id="phase_two_conflict_plan_known"),), text=" ", marker="m")
    state = state_for(ending_package())
    assert _state_summary(state)["story_complete"] is False
    assert "ending_marker" not in _state_summary(state)
    payload = _turn_payload(state, "Continue.")
    assert payload["story_complete"] is False


def test_shipped_package_declares_the_authored_ending():
    ending = PACKAGE.pacing.ending
    assert ending is not None
    assert ending.scene_id == "3C"
    assert ending.marker == "The story ends here."
    assert ending.when == (FactPredicate(fact_id="phase_two_conflict_plan_known", equals=True),)
    assert ending.text
    assert "Phase Two" in ending.text
