from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CARD_REVEAL = "k_sl_1a_b_r0"
F_R1 = "k_sl_1a_f_r1"
F_R2 = "k_sl_1a_f_r2"
F_STORYLET = "SL-1A-F"
CARD_STORYLET = "SL-1A-E"
NEW_FACT = "drawer_gap_pointed_out"
R1_DELIVERY = (
    "The drawer slides out. It holds a stapler, spare batteries, pens, and binder clips. "
    "A thin gap beneath its lower edge is wide enough for Kristin's fingers."
)
R2_DELIVERY = (
    "The initials are fresh, deep cuts. The drawer rides high in its frame. "
    "A thin gap beneath its lower edge is wide enough for Kristin's fingers."
)


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
        ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence)
        for candidate in candidates
        if candidate.action_evidence
    )
    return uniquely_matched_candidate(command, evidence)


def _provider(knowledge_id: str):
    knowledge = PACKAGE.knowledge_indexes.by_id[knowledge_id]
    return lambda _command: {
        "segments": [{"kind": "narration", "text": knowledge.delivery_text or knowledge.statement}],
        "selected_knowledge_ids": [knowledge_id],
    }


def _engine(knowledge_id: str) -> RuntimeEngine:
    state = RuntimeState.bootstrap(PACKAGE)
    return RuntimeEngine(state, _provider(knowledge_id))


def _has_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("Pull open the drawer.", F_R1),
        ("Pull the workstation drawer.", F_R1),
        ("Pull Michelle's workstation drawer.", F_R1),
        ("Open my drawer.", F_R1),
        ("Pull open the carved drawer with my fingers.", F_R1),
        ("Pull open the high-riding drawer.", F_R1),
        ("Open the drawer.", F_R1),
        ("Examine the carved KMS initials.", F_R2),
        ("Examine my initials carved into the drawer.", F_R2),
        ("Inspect the carved initials.", F_R2),
        ("Study the carving.", F_R2),
    ],
)
def test_drawer_gap_reveals_match_only_their_authored_actions(command: str, expected: str) -> None:
    handoff = _handoff(command)
    plain_match = _plain_match(command)

    assert handoff is not None
    assert handoff.candidate.id == expected
    assert plain_match is not None
    assert plain_match.id == expected


@pytest.mark.parametrize(
    "command",
    [
        "Search the workstation drawer.",
        "Examine the workstation drawer.",
        "Search the drawer interior.",
        "Search the open drawer.",
        "Search the KMS drawer.",
        "Examine the drawer's interior.",
        "Search the drawer.",
        "Search the kitchen.",
        "Inspect Michelle's workstation.",
        "Read the receipt.",
    ],
)
def test_drawer_gap_reveals_do_not_steal_unrelated_commands(command: str) -> None:
    assert _handoff(command) is None
    assert _plain_match(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "Feel beneath the drawer.",
        "Search the gap beneath the drawer.",
        "Feel along the gap in the drawer.",
        "Search beneath the drawer.",
    ],
)
def test_gap_commands_still_match_the_card_and_not_the_pointer(command: str) -> None:
    handoff = _handoff(command)
    plain_match = _plain_match(command)

    assert handoff is not None
    assert handoff.candidate.id == CARD_REVEAL
    assert plain_match is not None
    assert plain_match.id == CARD_REVEAL


def test_drawer_gap_realizations_have_exact_deliveries_and_fact_metadata() -> None:
    r1 = PACKAGE.knowledge_indexes.by_id[F_R1]
    r2 = PACKAGE.knowledge_indexes.by_id[F_R2]

    assert r1.delivery_text == R1_DELIVERY
    assert r2.delivery_text == R2_DELIVERY
    assert r1.entity_ids == r2.entity_ids == ("kristin", "michelle_drawer")
    assert r1.relevance.priority == r2.relevance.priority == 0
    assert r1.source.storylet_id == r2.source.storylet_id == F_STORYLET
    assert r1.source.realization_id == "SL-1A-F-R1"
    assert r2.source.realization_id == "SL-1A-F-R2"
    assert r1.establishes == r2.establishes
    assert r1.establishes[0].fact_id == NEW_FACT


def test_pointer_fires_then_leaves_the_card_candidate_available() -> None:
    engine = _engine(F_R1)
    engine.turn("Open the drawer.")

    assert F_STORYLET in engine.state.fired_event_ids
    assert _has_fact(engine.state, NEW_FACT)
    candidates = {candidate.id for candidate in engine.projector.project(engine.state, "player", "").candidates}
    assert CARD_REVEAL in candidates
    assert F_R1 not in candidates
    assert F_R2 not in candidates

    engine.provider = _provider(CARD_REVEAL)
    engine.turn("Search the gap beneath the drawer.")

    assert CARD_STORYLET in engine.state.fired_event_ids
    assert _has_fact(engine.state, "memory_card_recovered")
    candidates = {candidate.id for candidate in engine.projector.project(engine.state, "player", "").candidates}
    assert F_R1 not in candidates
    assert F_R2 not in candidates


def test_pointer_realization_r2_fires_its_own_storylet() -> None:
    engine = _engine(F_R2)
    engine.turn("Study the carving.")

    assert F_STORYLET in engine.state.fired_event_ids
    assert _has_fact(engine.state, NEW_FACT)
    assert not _has_fact(engine.state, "memory_card_recovered")


def test_pointer_fact_is_catalogued_but_read_by_no_gate_or_transition() -> None:
    assert NEW_FACT in PACKAGE.world.facts
    assert NEW_FACT in {fact.id for fact in PACKAGE.knowledge.facts}

    fact_claims = [
        knowledge
        for knowledge in PACKAGE.knowledge.knowledge
        if any(effect.fact_id == NEW_FACT for effect in knowledge.establishes)
    ]
    assert {knowledge.id for knowledge in fact_claims} == {F_R1, F_R2}
    assert all(not knowledge.requires for knowledge in fact_claims)

    assert all(
        predicate.fact_id != NEW_FACT
        for route in PACKAGE.storylet_routes.storylets
        for predicate in route.activation_conditions
    )
    assert all(
        NEW_FACT not in (*transition.required_dependencies,)
        and all(predicate.fact_id != NEW_FACT for predicate in transition.triggers)
        for transition in PACKAGE.pacing.transitions
    )
    assert all(
        NEW_FACT not in event.activation.all_facts_true and NEW_FACT not in event.activation.any_of
        for event in (*PACKAGE.storylet_routes.bridge_events, *PACKAGE.storylet_routes.resolution_events)
    )


def test_1a_transition_and_timer_remain_authored_values() -> None:
    transition = next(item for item in PACKAGE.pacing.transitions if item.id == "t_1a_1b")
    scene = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "1A")

    assert transition.source_scene_id == "1A"
    assert transition.target_scene_id == "1B"
    assert transition.priority == 10
    assert tuple(predicate.fact_id for predicate in transition.triggers) == (
        "michelle_lead_actionable",
        "patrol_return_pressure",
        "memory_card_recovered",
    )
    assert transition.required_dependencies == ("memory_card",)
    assert (scene.min_turns, scene.nudge_after_turns, scene.handoff_after_turns) == (8, 10, 13)
