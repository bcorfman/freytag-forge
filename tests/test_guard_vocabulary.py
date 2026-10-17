"""Guard vocabulary probes for scene-local public things and protected secrets."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import ActionEvidenceCandidate, uniquely_matched_candidate
from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
VALIDATOR = NarrationSafetyValidator()


def _state(scene_id: str) -> RuntimeState:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == scene_id)
    state = RuntimeState(package=PACKAGE, current_scene_id=scene_id, phase=scene.metadata.freytag_phase)
    apply_scene_placements(PACKAGE, state.facts, scene_id)
    return state


def _probe(scene_id: str, term: str) -> None:
    state = _state(scene_id)
    VALIDATOR.validate(
        state,
        deepcopy(state),
        ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=f"The {term} is visible."),)),
        KnowledgeProjector(),
        "Look around.",
    )


def test_gate_vocabulary_is_scene_local_before_any_reveal() -> None:
    _probe("1A", "house gate")
    _probe("1A", "front gate")
    with pytest.raises(ProposalValidationError, match="facility gate"):
        _probe("1A", "facility gate")

    with pytest.raises(ProposalValidationError):
        _probe("2A", "house gate")
    _probe("2A", "facility gate")
    _probe("2A", "front gate")
    _probe("2A", "gate")


def test_public_park_bench_is_nameable_before_the_card_is_read() -> None:
    _probe("1A", "park bench")

    with pytest.raises(ProposalValidationError, match="dead drop"):
        _probe("1A", "dead drop")


@pytest.mark.parametrize("scene_id", ("2A", "3B"))
def test_infrastructure_corridor_is_a_public_place_name(scene_id: str) -> None:
    _probe(scene_id, "infrastructure corridor")
    _probe(scene_id, "infrastructure corridors")


def test_corridor_reveal_still_requires_enter_command_evidence() -> None:
    item = PACKAGE.knowledge_indexes.by_id["k_sl_2a_c_r2"]
    candidate = ActionEvidenceCandidate(id=item.id, required_groups=item.action_evidence)

    assert uniquely_matched_candidate("Look at the infrastructure corridor.", (candidate,)) is None
    matched = uniquely_matched_candidate("Enter the infrastructure corridor.", (candidate,))
    assert matched is not None
    assert matched.id == "k_sl_2a_c_r2"


@pytest.mark.parametrize("term", ("JANUS", "Phase Two", "purge clock", "memory card"))
def test_existing_protected_secrets_remain_refused_in_scene_1a(term: str) -> None:
    with pytest.raises(ProposalValidationError):
        _probe("1A", term)
