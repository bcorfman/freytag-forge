from __future__ import annotations

from pathlib import Path

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CARD_REVEAL = "k_sl_1a_b_r0"
F_R1 = "k_sl_1a_f_r1"
F_R2 = "k_sl_1a_f_r2"
F_STORYLET = "SL-1A-F"
CARD_STORYLET = "SL-1A-E"


def _state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.update({CARD_STORYLET, F_STORYLET})
    return state


def _candidates(command: str):
    return KnowledgeProjector().project(_state(), "player", command).candidates


def _handoff(command: str):
    return uniquely_matched_authored_handoff(command, _candidates(command))


def _plain_match(command: str):
    candidates = _candidates(command)
    evidence = tuple(
        ActionEvidenceCandidate(
            id=candidate.id,
            required_groups=candidate.action_evidence,
            repeatable=candidate.repeatable,
        )
        for candidate in candidates
        if candidate.action_evidence
    )
    return uniquely_matched_candidate(command, evidence)


def test_gap_commands_uniquely_match_the_card_reveal() -> None:
    for command in (
        "Search the gap beneath the drawer.",
        "Feel under the drawer.",
    ):
        handoff = _handoff(command)
        plain_match = _plain_match(command)

        assert handoff is not None
        assert handoff.candidate.id == CARD_REVEAL
        assert plain_match is not None
        assert plain_match.id == CARD_REVEAL


def test_feel_gap_does_not_match_pointer_reveals() -> None:
    handoff = _handoff("Feel in the gap.")
    plain_match = _plain_match("Feel in the gap.")

    assert handoff is None or handoff.candidate.id not in {F_R1, F_R2}
    assert plain_match is None or plain_match.id not in {F_R1, F_R2}


def test_unrelated_commands_do_not_match_the_card_reveal() -> None:
    for command in ("Search the kitchen.", "Look at the fabric."):
        assert _handoff(command) is None
        assert _plain_match(command) is None

    handoff = _handoff("Pull out the drawer.")
    plain_match = _plain_match("Pull out the drawer.")
    assert handoff is not None
    assert handoff.candidate.id == F_R1
    assert plain_match is not None
    assert plain_match.id == F_R1
