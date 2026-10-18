from __future__ import annotations

from pathlib import Path

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    _matches_all,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.reveal_eligibility import ALREADY_ESTABLISHED, explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CARD_REVEAL = "k_sl_1a_b_r0"
CARD_FILES_REVEAL = "k_sl_1a_b_r1"
RECORDING_REVEAL = "k_sl_1a_b_r2"
RESEARCH_FILES_REVEAL = "k_sl_1a_d_r1"
RESEARCH_FILES_STORYLET = "SL-1A-D"


def _provider(knowledge_id: str):
    knowledge = PACKAGE.knowledge_indexes.by_id[knowledge_id]
    return lambda _command: {
        "segments": [{"kind": "narration", "text": knowledge.delivery_text or knowledge.statement}],
        "selected_knowledge_ids": [knowledge_id],
    }


def _engine(knowledge_id: str) -> RuntimeEngine:
    return RuntimeEngine(RuntimeState.bootstrap(PACKAGE), _provider(knowledge_id))


def _has_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


def _projected(state: RuntimeState, command: str):
    return KnowledgeProjector().project(state, "player", command).candidates


def _handoff(state: RuntimeState, command: str):
    return uniquely_matched_authored_handoff(command, _projected(state, command))


def test_b_r1_establishes_research_files_and_closes_d_r1() -> None:
    engine = _engine(CARD_REVEAL)
    engine.turn("Feel underneath the drawer.")
    engine.provider = _provider(CARD_FILES_REVEAL)
    engine.turn("Insert Michelle's memory card into my laptop.")

    for fact_id in (
        "michelle_warning_known",
        "continuity_initiative_known",
        "michelle_abduction_suspicion",
        "michelle_lead_actionable",
    ):
        assert _has_fact(engine.state, fact_id), f"b_r1 should establish {fact_id}"

    d_r1 = PACKAGE.knowledge_indexes.by_id[RESEARCH_FILES_REVEAL]
    commands = (
        "Open Michelle's saved files and examine the information about the Continuity Initiative.",
        "Read Michelle's remaining files.",
    )
    for command in commands:
        assert _matches_all(d_r1.action_evidence, command), f"d_r1 words should match: {command}"
        eligibility = explain_reveal(engine.state, "player", d_r1)
        assert not eligibility.eligible, "d_r1 must not be eligible after b_r1"
        assert eligibility.reason == ALREADY_ESTABLISHED, "d_r1 must be filtered as already established"
        assert RESEARCH_FILES_REVEAL not in {candidate.id for candidate in _projected(engine.state, command)}
        handoff = _handoff(engine.state, command)
        assert handoff is None or handoff.candidate.id != RESEARCH_FILES_REVEAL


def test_b_r2_leaves_d_r1_as_the_research_files_fallback() -> None:
    engine = _engine(CARD_REVEAL)
    engine.turn("Feel underneath the drawer.")
    engine.provider = _provider(RECORDING_REVEAL)
    engine.turn("Play the damaged recording on the memory card.")

    assert _has_fact(engine.state, "michelle_warning_known"), "b_r2 should establish the warning fact"
    assert _has_fact(engine.state, "memory_card_recovered"), "b_r0 should recover the memory card"
    assert not _has_fact(engine.state, "continuity_initiative_known"), "b_r2 must not establish continuity"
    assert not _has_fact(engine.state, "michelle_lead_actionable"), "b_r2 must not establish an actionable lead"

    if RESEARCH_FILES_STORYLET not in engine.state.active_event_ids:
        # The D storylet is the fallback route for players who read the recording first.
        engine.state.active_event_ids.update({RESEARCH_FILES_STORYLET})

    d_r1 = PACKAGE.knowledge_indexes.by_id[RESEARCH_FILES_REVEAL]
    eligibility = explain_reveal(engine.state, "player", d_r1)
    assert eligibility.eligible, "d_r1 should be eligible after only the recording"
    assert eligibility.reason == "eligible"
    handoff = _handoff(engine.state, "Read Michelle's remaining files.")
    assert handoff is not None, "the remaining-files command should resolve to d_r1"
    assert handoff.candidate.id == RESEARCH_FILES_REVEAL


def test_word_match_alone_cannot_break_b_r1_d_r1_tie() -> None:
    b_r1 = PACKAGE.knowledge_indexes.by_id[CARD_FILES_REVEAL]
    d_r1 = PACKAGE.knowledge_indexes.by_id[RESEARCH_FILES_REVEAL]
    command = "Open the files on Michelle's memory card."
    assert _matches_all(b_r1.action_evidence, command), "b_r1 action words should match"
    assert _matches_all(d_r1.action_evidence, command), "d_r1 action words should match"

    candidates = tuple(
        ActionEvidenceCandidate(id=item.id, required_groups=item.action_evidence) for item in (b_r1, d_r1)
    )
    assert uniquely_matched_candidate(command, candidates) is None, "a raw evidence tie must remain unresolved"
