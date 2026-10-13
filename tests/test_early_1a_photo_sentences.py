from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state(scene_id: str) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    return state


def _verdict(scene_id: str, text: str) -> tuple[str, str]:
    state = _state(scene_id)
    try:
        RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": text}]}).turn("Look around.")
    except ProposalValidationError as error:
        return "rejected", error.code or type(error).__name__
    return "accepted", ""


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("Kristin looks at a photo.", ("accepted", "")),
        ("The phone shows a photograph.", ("accepted", "")),
        ("Kristin sees a picture on the wall.", ("accepted", "")),
        ("The phone shows a photo of the two friends.", ("accepted", "")),
        ("Michelle's photograph is on the screen.", ("rejected", "narration_known_term_leak")),
    ),
)
def test_early_1a_photo_sentence_verdicts(text: str, expected: tuple[str, str]) -> None:
    assert _verdict("1A", text) == expected
