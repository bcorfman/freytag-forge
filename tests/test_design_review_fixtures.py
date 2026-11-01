"""Small, state-exact fixtures for the ChatGPT design review findings."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _scene_state(scene_id: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    return state


def _late_scene_state(scene_id: str) -> RuntimeState:
    order = {scene.metadata.scene_id: index for index, scene in enumerate(PACKAGE.scenes)}
    scene_index = order[scene_id]
    state = _scene_state(scene_id)
    for earlier_scene in PACKAGE.scenes[:scene_index]:
        state._assert_scene_entry_fact(earlier_scene.metadata.scene_id)
    for item in PACKAGE.knowledge.knowledge:
        if not item.available_in_scenes or not all(
            order[available] <= scene_index for available in item.available_in_scenes
        ):
            continue
        for operation in item.establishes:
            if operation.op == "assert":
                value = str(operation.value).lower() if isinstance(operation.value, bool) else str(operation.value)
                state.facts.assert_fact(Fact(predicate=operation.fact_id, subject="story", value=value))
    return state


def _knowledge_item(knowledge_id: str):
    return next(item for item in PACKAGE.knowledge.knowledge if item.id == knowledge_id)


def _assert_not_earned(state: RuntimeState, knowledge_id: str) -> None:
    item = _knowledge_item(knowledge_id)
    assert not KnowledgeProjector._established(item, state)


def _rejected_code(state: RuntimeState, text: str) -> str:
    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, _narration(text)).turn("Search the room.")
    return caught.value.code or type(caught.value).__name__


def _assert_story_facts(state: RuntimeState, *fact_ids: str) -> None:
    for fact_id in fact_ids:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))


def _narration(text: str):
    def provider(_player_input: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": text}]}

    return provider


def test_ordinary_name_accepted() -> None:
    """Finding 1: name guards must allow ordinary public scene names."""

    state = _scene_state("1A")
    ordinary = "The drawer remains in Michelle's workstation."

    # The drawer is a public item declared in scene 1A's item placements.
    result = RuntimeEngine(state, _narration(ordinary)).turn("Search the drawer.")
    assert ordinary in result.narration

    # Rebecca is not yet nameable in 1A, so the paired protected case is rejected.
    assert _rejected_code(state, "Rebecca is in the room.") == "narration_known_term_leak"

    other_state = _scene_state("1B")
    # The park is the public location declared by scene 1B's metadata.
    other = "The park surrounds the pursuit."
    other_result = RuntimeEngine(other_state, _narration(other)).turn("Search the park.")
    assert other in other_result.narration


@pytest.mark.parametrize(
    ("scene_id", "knowledge_id", "text", "expected_code"),
    (
        pytest.param(
            "2C",
            "k_sl_3c_e_r1",
            "Phase Two is active.",
            "protected_narration_leak",
            id="protected-knowledge-term",
        ),
        pytest.param(
            "1A",
            "k_sl_2a_c_r5",
            "The genuine cooling-water pressure fault is dangerous.",
            "narration_known_term_leak",
            id="declared-leak-term",
        ),
        pytest.param(
            "1A",
            "k_sl_2c_d_r3",
            "Rebecca is in the room.",
            "narration_known_term_leak",
            id="unnameable-entity",
        ),
    ),
)
def test_premature_secret_rejected(scene_id: str, knowledge_id: str, text: str, expected_code: str) -> None:
    """Finding 1: name guards reject each protected-term kind before its reveal."""

    state = _scene_state(scene_id)
    _assert_not_earned(state, knowledge_id)
    if "Rebecca" in text:
        scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
        assert "rebecca" not in {
            scene.metadata.location_id,
            *scene.metadata.participant_ids,
            *scene.metadata.item_ids,
        }
        assert all(
            not KnowledgeProjector._established(item, state)
            for item in PACKAGE.knowledge.knowledge
            if "rebecca" in item.entity_ids
        )
    assert _rejected_code(state, text) == expected_code


def test_skipped_reveal() -> None:
    """Finding 1: a skipped earlier reveal keeps its protected-term guard."""

    reveal = _knowledge_item("k_sl_3c_e_r1")
    state = _late_scene_state("3C")
    skipped_facts = tuple(reveal.establishes)
    for operation in skipped_facts:
        if operation.op == "assert":
            state.facts.retract_fact(Fact(predicate=operation.fact_id, subject="story", value="true"))
    assert all(
        not state.facts.matching(operation.fact_id, subject="story")
        for operation in skipped_facts
        if operation.op == "assert"
    )
    protected_text = "Phase Two was designed to provoke conflict."
    assert _rejected_code(state, protected_text) == "protected_narration_leak"

    earned_state = copy.deepcopy(state)
    for operation in skipped_facts:
        if operation.op == "assert":
            earned_state.facts.assert_fact(Fact(predicate=operation.fact_id, subject="story", value="true"))
    result = RuntimeEngine(earned_state, _narration(protected_text)).turn("Search the archive.")
    assert protected_text in result.narration


def test_missed_pointer() -> None:
    """Finding 2: a delivered cue receives one stronger authored nudge."""

    state = _scene_state("1A")
    package = PACKAGE.model_copy(
        update={
            "deliveries": tuple(
                delivery.model_copy(update={"escalation_text": "The workstation still holds a lead worth examining."})
                if delivery.fact_id == "continuity_initiative_known"
                else delivery
                for delivery in PACKAGE.deliveries
            )
        }
    )
    state.package = package
    engine = RuntimeEngine(state, _narration("The drawer remains in Michelle's workstation."))
    engine.turn("Search the drawer.")
    for _ in range(11):
        engine.turn("Inspect the workstation.")

    assert state.cue_stages[-1].stage == 2
    assert state.cue_stages[-1].fact_id == "continuity_initiative_known"
    assert state.delivered_cue_ids == ("continuity_initiative_known",)


def test_matcher_tie() -> None:
    """Finding 3: reveal matching refuses to choose between tied candidates."""

    first = ActionEvidenceCandidate(id="first", required_groups=(("inspect",), ("drawer",)))
    second = ActionEvidenceCandidate(id="second", required_groups=(("inspect",), ("drawer",)))

    assert uniquely_matched_candidate("Inspect the drawer.", (first, second)) is None


def test_more_than_four_eligible() -> None:
    """The prompt stays capped while exact matching sees the full universe."""

    state = _scene_state("1A")
    _assert_story_facts(state, "memory_card_recovered", "michelle_warning_known")
    state.turn_index = 4
    RuntimeEngine(state, _narration("The workstation is quiet."))._activate_pacing()

    eligible = tuple(
        item
        for item in PACKAGE.knowledge.knowledge
        if "1A" in item.available_in_scenes and explain_reveal(state, "player", item).eligible
    )
    assert len(eligible) == 5
    all_candidates = tuple(KnowledgeProjector._candidate(item) for item in eligible)
    handoff = uniquely_matched_authored_handoff("Inspect the reflective tape.", all_candidates)
    assert handoff is not None
    assert handoff.candidate.id == "k_sl_1a_c_r2"

    projection = KnowledgeProjector().project(state, "player", "Inspect the reflective tape.")
    assert len(projection.candidates) == 4
    assert "k_sl_1a_c_r2" not in {candidate.id for candidate in projection.candidates}
    assert len(projection.reveal_universe) == 5
    assert projection.reveal_universe[-1].id == "k_sl_1a_c_r2"
