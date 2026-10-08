"""Holding-block names become available only after Michelle's route is earned."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _proposal(text: str) -> ResolvedTurnProposal:
    return ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=text),))


def _state(scene_id: str, knowledge_id: str | None = None) -> RuntimeState:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == scene_id)
    state = RuntimeState(package=PACKAGE, current_scene_id=scene_id, phase=scene.metadata.freytag_phase)
    if knowledge_id is not None:
        knowledge = PACKAGE.knowledge_indexes.by_id[knowledge_id]
        for effect in knowledge.establishes:
            state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value=str(effect.value).lower()))
    return state


def _validate(scene_id: str, text: str, knowledge_id: str | None = None) -> None:
    state = _state(scene_id, knowledge_id)
    NarrationSafetyValidator().validate(
        state,
        deepcopy(state),
        _proposal(text),
        KnowledgeProjector(),
        "Enter Michelle's holding block.",
    )


def test_earned_holding_block_allows_its_parent_location() -> None:
    _validate(
        "2C",
        "Kristin enters the holding block on the detention level.",
        "k_sl_2c_d_r1",
    )


def test_unearned_holding_block_is_rejected() -> None:
    with pytest.raises(ProposalValidationError, match="holding block"):
        _validate("2C", "Kristin enters the holding block.")


@pytest.mark.parametrize("name", ["detention level", "holding block"])
def test_scene_1a_cannot_name_the_detention_locations(name: str) -> None:
    with pytest.raises(ProposalValidationError, match=name):
        _validate("1A", f"Kristin enters the {name}.")


def test_earning_holding_block_makes_detention_level_nameable() -> None:
    _validate("2C", "Kristin enters the detention level.", "k_sl_2c_d_r1")
