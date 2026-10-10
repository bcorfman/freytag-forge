from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import ActionEvidenceCandidate, uniquely_matched_candidate
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
RECORDS_ID = "detention_medical_records"
ORIGINAL_RECORDS_REVEAL = "k_sl_3a_b_r1"
MEDICAL_ENTRY_REVEAL = "k_sl_3a_b_r2"
FOLLOWUP_REVEAL = "k_sl_3a_e_r1"
RECORD_COMMANDS = (
    "Read the experiment records.",
    "Examine the experiment records.",
    "Open the experiment records.",
    "Inspect the medical records.",
    "Review the survivor records.",
)
DELIVERY_TEXT = (
    "Michelle shows Kristin experiment records. They prove planned survivors were conditioned to support Charles's "
    "story. The senior official waits among the government prisoners."
)


def _state(*, michelle_reached: bool = False) -> RuntimeState:
    state = RuntimeState(package=PACKAGE, current_scene_id="3A", phase="crisis")
    state._assert_scene_entry_fact("3A")
    if michelle_reached:
        state.facts.assert_fact(Fact(predicate="michelle_reached", subject="story", value="true"))
    return state


def _provider(knowledge_id: str):
    knowledge = PACKAGE.knowledge_indexes.by_id[knowledge_id]
    text = knowledge.delivery_text or knowledge.statement
    return lambda _command: {
        "segments": [{"kind": "narration", "text": text, "grounding_ids": [knowledge_id]}],
        "selected_knowledge_ids": [knowledge_id],
    }


def _engine(state: RuntimeState, knowledge_id: str) -> RuntimeEngine:
    return RuntimeEngine(state, _provider(knowledge_id))


def _candidate_ids(engine: RuntimeEngine, command: str) -> set[str]:
    engine._activate_pacing()  # noqa: SLF001 - project the same active routes as a turn.
    return {candidate.id for candidate in engine.projector.project(engine.state, "player", command).candidates}


def _matched_id(engine: RuntimeEngine, command: str) -> str | None:
    candidates = engine.projector.project(engine.state, "player", command).candidates
    evidence = tuple(
        ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence) for candidate in candidates
    )
    matched = uniquely_matched_candidate(command, evidence)
    return matched.id if matched is not None else None


def _has_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


def _medical_entry_engine() -> RuntimeEngine:
    engine = _engine(_state(michelle_reached=True), MEDICAL_ENTRY_REVEAL)
    engine.turn("Enter the medical level.")
    return engine


@pytest.mark.parametrize("command", RECORD_COMMANDS)
def test_medical_entry_records_commands_uniquely_match_the_followup(command: str) -> None:
    engine = _medical_entry_engine()

    assert _matched_id(engine, command) == FOLLOWUP_REVEAL


def test_records_first_keeps_original_route_and_closes_followup() -> None:
    engine = _engine(_state(michelle_reached=True), ORIGINAL_RECORDS_REVEAL)
    engine.turn("Read the experiment records.")

    assert "SL-3A-B" in engine.state.fired_event_ids
    assert _has_fact(engine.state, "behavioral_experiments_known")
    assert _has_fact(engine.state, "conditioned_release_plan_known")
    assert FOLLOWUP_REVEAL not in _candidate_ids(engine, "Read the experiment records.")


def test_followup_asserts_conditioning_fact_once_and_then_is_not_a_candidate() -> None:
    engine = _medical_entry_engine()
    assert _matched_id(engine, "Read the experiment records.") == FOLLOWUP_REVEAL

    engine.provider = _provider(FOLLOWUP_REVEAL)
    engine.turn("Read the experiment records.")

    assert "SL-3A-E" in engine.state.fired_event_ids
    assert _has_fact(engine.state, "conditioned_release_plan_known")
    assert FOLLOWUP_REVEAL not in _candidate_ids(engine, "Read the experiment records.")


def test_records_reveals_wait_for_michelle_and_followup_waits_for_medical_entry() -> None:
    before_michelle = _engine(_state(), MEDICAL_ENTRY_REVEAL)
    assert ORIGINAL_RECORDS_REVEAL not in _candidate_ids(before_michelle, "Read the experiment records.")
    assert FOLLOWUP_REVEAL not in _candidate_ids(before_michelle, "Read the experiment records.")

    after_michelle = _engine(_state(michelle_reached=True), MEDICAL_ENTRY_REVEAL)
    assert ORIGINAL_RECORDS_REVEAL in _candidate_ids(after_michelle, "Read the experiment records.")
    assert FOLLOWUP_REVEAL not in _candidate_ids(after_michelle, "Read the experiment records.")


@pytest.mark.parametrize("route", [ORIGINAL_RECORDS_REVEAL, FOLLOWUP_REVEAL])
def test_followup_is_not_eligible_when_conditioning_plan_is_already_known(route: str) -> None:
    state = _state(michelle_reached=True)
    state.facts.assert_fact(Fact(predicate="behavioral_experiments_known", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="conditioned_release_plan_known", subject="story", value="true"))
    engine = _engine(state, route)
    engine._activate_pacing()  # noqa: SLF001 - exercise authored activation gates.

    assert FOLLOWUP_REVEAL not in _candidate_ids(engine, "Read the experiment records.")


def test_medical_entry_to_official_and_scene_transition_do_not_need_followup() -> None:
    engine = _medical_entry_engine()

    assert _matched_id(engine, "Speak with the senior official.") == "k_sl_3a_d_r1"
    engine.provider = _provider("k_sl_3a_d_r1")
    engine.turn("Speak with the senior official.")
    assert _has_fact(engine.state, "military_override_codes_available")
    assert not _has_fact(engine.state, "conditioned_release_plan_known")

    engine.state.facts.assert_fact(Fact(predicate="command_levels_assault_underway", subject="story", value="true"))
    engine.state.turn_index = 20
    engine._apply_authored_transition()  # noqa: SLF001 - verify the authored 3A -> 3B route.
    assert engine.state.current_scene_id == "3B"


def test_records_are_grounded_and_shown_after_medical_entry_without_pre_reveal_contents() -> None:
    engine = _medical_entry_engine()
    records = next(item for item in PACKAGE.world.items if item.id == RECORDS_ID)
    assert records.name == "detention medical records"
    assert world_for(PACKAGE, engine.state.facts).parent(RECORDS_ID) == "medical_level"

    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=engine.state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )
    provider._selected_names = [records.name]
    prompt = provider.assemble_turn_prompt("Look around the medical level.")
    user_prompt = provider._section_user_prompt(prompt["context"])

    assert f"- {records.name}. Place: in the medical level." in user_prompt
    assert DELIVERY_TEXT not in user_prompt
    assert PACKAGE.knowledge_indexes.by_id[FOLLOWUP_REVEAL].statement not in user_prompt
