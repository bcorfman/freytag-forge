from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.knowledge import RevealCandidate
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
SCENE_2A_CANDIDATES = tuple(
    RevealCandidate(
        id=item.id,
        statement=item.statement,
        earn_when=item.earn_when,
        must_convey=item.must_convey,
        action_evidence=item.action_evidence,
        delivery_text=item.delivery_text,
    )
    for item in PACKAGE.knowledge.knowledge
    if "2A" in item.available_in_scenes and item.action_evidence
)


@pytest.mark.parametrize(
    "player_input",
    [
        "Diagnose the real cooling-water pressure fault for the supervisor.",
        "Read the pressure gauge and give a precise explanation of the ventilation fault.",
    ],
)
def test_2a_supervisor_diagnosis_selects_convincing_inspection(player_input: str) -> None:
    handoff = uniquely_matched_authored_handoff(player_input, SCENE_2A_CANDIDATES)

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_2a_c_r5"


@pytest.mark.parametrize(
    "player_input",
    [
        "Present my inspection forms to the supervisor.",
        "Follow the supervisor through the nearby door.",
    ],
)
def test_2a_unrelated_actions_do_not_select_an_inspection_outcome(player_input: str) -> None:
    handoff = uniquely_matched_authored_handoff(player_input, SCENE_2A_CANDIDATES)

    assert handoff is None or handoff.candidate.id not in {"k_sl_2a_c_r5", "k_sl_2a_c_r6"}
