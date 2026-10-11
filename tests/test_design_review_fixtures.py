"""Small, state-exact fixtures for the ChatGPT design review findings."""

from __future__ import annotations

from pathlib import Path

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

    RuntimeEngine(state, _narration("The drawer remains in Michelle's workstation.")).turn("Search the drawer.")


def test_premature_secret_rejected() -> None:
    """Finding 1: name guards must reject a protected term before its reveal."""

    state = _scene_state("1A")

    try:
        RuntimeEngine(state, _narration("JANUS is in the room.")).turn("Search the room.")
    except ProposalValidationError as error:
        assert error.code == "protected_narration_leak"
    else:
        raise AssertionError("an unearned protected term was accepted")


def test_skipped_reveal() -> None:
    """Finding 1: a skipped earlier reveal keeps its protected-term guard."""

    state = _scene_state("2B")

    try:
        RuntimeEngine(state, _narration("JANUS is in the archive.")).turn("Search the archive.")
    except ProposalValidationError as error:
        assert error.code == "protected_narration_leak"
    else:
        raise AssertionError("a skipped reveal's protected term was accepted")


def test_missed_pointer() -> None:
    """Finding 2: a delivered cue is spent without an escalation nudge."""

    state = _scene_state("1A")
    engine = RuntimeEngine(state, _narration("The drawer remains in Michelle's workstation."))
    engine.turn("Search the drawer.")
    cue_ids = [state.last_turn_delivery.cue_fact_id]
    for _ in range(3):
        engine.turn("Inspect the workstation.")
        cue_ids.append(state.last_turn_delivery.cue_fact_id)

    # CURRENT DEFECT (review Finding 2): no escalation; nudge_after_turns unused.
    assert cue_ids.count("continuity_initiative_known") == 1
    assert state.delivered_cue_ids == ("continuity_initiative_known",)


def test_matcher_tie() -> None:
    """Finding 3: reveal matching refuses to choose between tied candidates."""

    first = ActionEvidenceCandidate(id="first", required_groups=(("inspect",), ("drawer",)))
    second = ActionEvidenceCandidate(id="second", required_groups=(("inspect",), ("drawer",)))

    assert uniquely_matched_candidate("Inspect the drawer.", (first, second)) is None


def test_more_than_four_eligible() -> None:
    """Finding 4: measurement must expose the four-candidate projection cap."""

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
