"""Names of characters present in a scene are safe to narrate."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _narrate(text: str) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    payload = {"segments": [{"kind": "narration", "text": text, "grounding_ids": []}]}
    RuntimeEngine(state, lambda _player_input: payload).turn("Question the officer.")


@pytest.mark.parametrize(
    "text",
    [
        "The officer says Dr. McGehee is missing.",
        "The officer asks about Michelle McGehee.",
        "Dr. Michelle McGehee is missing.",
    ],
)
def test_scene_participant_names_are_available(text: str) -> None:
    _narrate(text)


def test_non_nameable_character_name_is_rejected() -> None:
    with pytest.raises(ProposalValidationError) as exc_info:
        _narrate("Brandon Corfman is missing.")

    assert exc_info.value.code == "narration_known_term_leak"


def test_later_scene_protected_term_is_rejected() -> None:
    with pytest.raises(ProposalValidationError) as exc_info:
        _narrate("The officer describes phase two.")

    assert exc_info.value.code in {"protected_narration_leak", "narration_known_term_leak"}
