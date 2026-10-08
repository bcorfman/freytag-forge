"""Place names are available only when the scene makes them nameable."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _proposal(text: str) -> ResolvedTurnProposal:
    return ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=text),))


def _validate(scene_id: str, text: str) -> None:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == scene_id)
    state = RuntimeState(package=PACKAGE, current_scene_id=scene_id, phase=scene.metadata.freytag_phase)
    NarrationSafetyValidator().validate(
        state,
        deepcopy(state),
        _proposal(text),
        KnowledgeProjector(),
        "Search the area.",
    )


def test_owned_place_name_is_available_in_scene() -> None:
    _validate("3A", "The group reaches the broadcast chamber.")


def test_owned_place_name_is_unavailable_before_owner_enters_scene() -> None:
    with pytest.raises(ProposalValidationError, match="broadcast chamber") as caught:
        _validate("1B", "The group reaches the broadcast chamber.")

    assert caught.value.code == "narration_known_term_leak"


def test_place_name_in_situation_allows_plural_narration_form() -> None:
    _validate("2B", "The team heads toward the detention level.")


def test_place_name_not_in_situation_remains_unavailable() -> None:
    with pytest.raises(ProposalValidationError, match="detention level") as caught:
        _validate("1A", "The team heads toward the detention level.")

    assert caught.value.code == "narration_known_term_leak"
