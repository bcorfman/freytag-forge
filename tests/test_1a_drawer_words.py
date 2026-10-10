from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _projected_handoff(player_input: str):
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-E")
    projection = KnowledgeProjector().project(state, "player", "")
    return uniquely_matched_authored_handoff(player_input, projection.candidates)


@pytest.mark.parametrize(
    "player_input",
    [
        "Examine the drawer's lower edge.",
        "Feel along the drawer's lower edge.",
        "Inspect the bottom edge of the drawer.",
        "Check the lower edge of the KMS drawer.",
        "Search the lower edge of Michelle's workstation.",
        "Feel the drawer's lower edge.",
        "Inspect the gap beneath the KMS drawer.",
        "Search beneath the drawer.",
        "Look under the KMS drawer.",
        "Look underneath the drawer.",
        "Check the underside of the workstation.",
        "Feel beneath the drawer.",
        "Check the bottom of the drawer.",
    ],
)
def test_1a_drawer_words_select_drawer_reveal(player_input: str) -> None:
    handoff = _projected_handoff(player_input)

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_1a_b_r0"


@pytest.mark.parametrize(
    "player_input",
    [
        "Open the KMS drawer.",
        "Open the high-riding drawer.",
        "Inspect the workstation.",
        "Inspect the drawer.",
        "Examine the drawer's top edge.",
        "Inspect the edge of the drawer.",
        "Pull the drawer open.",
        "Lift the KMS drawer.",
        "Open the workstation drawer.",
        "Take the note.",
    ],
)
def test_1a_drawer_words_select_nothing(player_input: str) -> None:
    assert _projected_handoff(player_input) is None


@pytest.mark.parametrize("player_input", ["Inspect the back door.", "Inspect the gate."])
def test_1a_other_places_do_not_select_drawer_reveal(player_input: str) -> None:
    handoff = _projected_handoff(player_input)

    assert handoff is None or handoff.candidate.id != "k_sl_1a_b_r0"


def test_1a_handoff_cue_mentions_lower_edge_gap() -> None:
    handoff = next(handoff for handoff in PACKAGE.deliveries if handoff.scene_id == "1A")

    assert "beneath its lower edge" in handoff.cue_text
