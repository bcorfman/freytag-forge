from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _projected_handoff(player_input: str):
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    state.active_event_ids.add("SL-2A-B")
    state.facts.assert_fact(Fact(predicate="facility_infiltration_needed", subject="story", value="true"))
    projection = KnowledgeProjector().project(state, "player", "")
    return uniquely_matched_authored_handoff(player_input, projection.candidates)


@pytest.mark.parametrize(
    "player_input",
    [
        "Ask Brandon about the inspection forms.",
        "Ask Brandon about the blank inspector forms.",
        "Ask Brandon about the credentials.",
        "Fill out the blank inspector forms with Brandon.",
        "Show Brandon the inspector forms.",
    ],
)
def test_2a_forms_words_select_forms_reveal(player_input: str) -> None:
    handoff = _projected_handoff(player_input)

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_2a_b_r2"


@pytest.mark.parametrize(
    "player_input",
    [
        "Ask Brandon how to reach the gate.",
        "Ask Brandon about the facility layout.",
        "Ask Brandon about the cooling system.",
        "Search the hideout for a map of the facility.",
        "Study the facility from the service road.",
    ],
)
def test_2a_unrelated_words_do_not_select_forms_reveal(player_input: str) -> None:
    handoff = _projected_handoff(player_input)

    assert handoff is None or handoff.candidate.id != "k_sl_2a_b_r2"


def test_2a_inspection_forms_question_is_unique() -> None:
    handoff = _projected_handoff("Ask Brandon about the inspection forms.")

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_2a_b_r2"
