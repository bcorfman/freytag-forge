"""Fixed scene things do not expose unavailable knowledge when named."""

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


def test_1b_narration_can_name_present_fixed_thing_before_card_read() -> None:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == "1B")
    state = RuntimeState(package=PACKAGE, current_scene_id="1B", phase=scene.metadata.freytag_phase)
    candidate_state = deepcopy(state)

    NarrationSafetyValidator().validate(
        state,
        candidate_state,
        _proposal("The park bench waits beneath the trees."),
        KnowledgeProjector(),
        "Search the park bench.",
    )


def test_1a_narration_cannot_name_unread_memory_card() -> None:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == "1A")
    state = RuntimeState(package=PACKAGE, current_scene_id="1A", phase=scene.metadata.freytag_phase)
    candidate_state = deepcopy(state)

    with pytest.raises(ProposalValidationError) as caught:
        NarrationSafetyValidator().validate(
            state,
            candidate_state,
            _proposal("The memory card lies on the floor."),
            KnowledgeProjector(),
            "Search the kitchen.",
        )

    assert caught.value.code == "narration_known_term_leak"
