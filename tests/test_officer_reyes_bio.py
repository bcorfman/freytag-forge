from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from tests import test_prompt_presence

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
OFFICER_BIO = (
    "A young, polite federal patrol officer who works from a printed list and does not like what the list asks of him."
)
OFFICER_LINE = f"- Officer Reyes is {OFFICER_BIO[0].lower()}{OFFICER_BIO[1:]}"


def test_package_character_uses_the_officer_narrator_bio() -> None:
    character = next(item for item in PACKAGE.characters if item.id == "patrol_officer")
    officer = next(item for item in PACKAGE.world.npcs if item.id == "patrol_officer")

    assert character.bio == officer.narrator_bio


def test_officer_narrator_bio_is_exact_and_does_not_hide_a_purpose() -> None:
    officer = next(item for item in PACKAGE.world.npcs if item.id == "patrol_officer")

    assert officer.narrator_bio == OFFICER_BIO
    assert "covert" not in officer.narrator_bio
    assert "hidden purpose" not in officer.narrator_bio.lower()


def test_officer_is_a_participant_only_in_1a() -> None:
    scenes = [scene.metadata.scene_id for scene in PACKAGE.scenes if "patrol_officer" in scene.metadata.participant_ids]

    assert scenes == ["1A"]


def test_officer_line_is_absent_before_the_patrol_arrives() -> None:
    state, _engine = _scene_1a_engine()
    assert OFFICER_LINE not in test_prompt_presence._characters(state, "Look around.")


def test_officer_line_enters_the_prompt_after_the_patrol_enters_the_kitchen() -> None:
    state, engine = _scene_1a_engine()

    for _turn in range(7):
        engine.turn("Wait and observe.")

    assert state.turn_index == 7
    characters = test_prompt_presence._characters(state, "Wait and observe.")
    assert OFFICER_LINE in characters


def _scene_1a_engine():
    state = RuntimeState.bootstrap(PACKAGE)

    def provider(_command):
        return {"segments": [{"kind": "narration", "text": "The house remains quiet."}]}

    return state, RuntimeEngine(state, provider)
