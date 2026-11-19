from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(ROOT)
PHONE_REALIZATIONS = ("SL-1A-J-R1", "SL-1A-J-R2", "SL-1A-J-R3")
PHONE_KNOWLEDGE = ("k_sl_1a_j_r1", "k_sl_1a_j_r2", "k_sl_1a_j_r3")


def _knowledge() -> dict[str, object]:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _routes() -> dict:
    return {route.id: route for route in PACKAGE.storylet_routes.storylets}


def _candidate_ids(command: str, *, true_facts: tuple[str, ...] = (), false_facts: tuple[str, ...] = ()) -> set[str]:
    state = RuntimeState.bootstrap(PACKAGE)
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    for fact_id in false_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="false"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    engine._activate_pacing()
    return {candidate.id for candidate in engine.projector.project(state, "player", command).candidates}


def test_phone_thread_storylet_is_declared():
    storylet = _routes()["SL-1A-J"]
    assert storylet.scene_id == "1A"
    assert [option.id for option in storylet.realizations] == list(PHONE_REALIZATIONS)
    assert (storylet.earliest_turn, storylet.target_turn, storylet.latest_turn) == (0, 5, 11)


def test_phone_thread_facts_are_declared_everywhere():
    fact_ids = {"michelle_text_read", "kristin_calls_read"}
    route_facts = {
        operation.fact_id
        for route in PACKAGE.storylet_routes.storylets
        for realization in route.realizations
        for operation in realization.operations
    }
    route_facts.update(
        operation.fact_id
        for event in (*PACKAGE.storylet_routes.bridge_events, *PACKAGE.storylet_routes.resolution_events)
        for operation in event.operations
    )
    assert fact_ids <= {fact.id for fact in PACKAGE.knowledge.facts}
    assert fact_ids <= set(PACKAGE.world.facts)
    assert fact_ids <= route_facts


def test_the_text_is_offered_when_the_patrol_is_away():
    for command in ("Unlock Michelle's phone.", "Read the messages on Michelle's phone."):
        ids = _candidate_ids(command, false_facts=("patrol_in_house",))
        assert "k_sl_1a_j_r1" in ids
        assert not {"k_sl_1a_j_r2", "k_sl_1a_j_r3"} & ids


def test_the_uneasy_text_is_offered_when_the_officer_is_in_the_kitchen():
    for command in ("Unlock Michelle's phone.", "Read the messages on Michelle's phone."):
        ids = _candidate_ids(command, true_facts=("patrol_in_house",))
        assert "k_sl_1a_j_r2" in ids
        assert not {"k_sl_1a_j_r1", "k_sl_1a_j_r3"} & ids


def test_the_historical_password_command_earns_the_text():
    assert "k_sl_1a_j_r1" in _candidate_ids("Type in the password.", false_facts=("patrol_in_house",))


def test_the_calls_need_the_text_first():
    assert "k_sl_1a_j_r3" not in _candidate_ids("Check the call log.", true_facts=("patrol_in_house",))
    assert "k_sl_1a_j_r3" in _candidate_ids("Check the call log.", true_facts=("patrol_in_house", "michelle_text_read"))


def test_delivery_texts_are_exactly_the_approved_lines():
    entries = _knowledge()
    assert [entry.id for entry in (entries[knowledge_id] for knowledge_id in PHONE_KNOWLEDGE)] == list(PHONE_KNOWLEDGE)
    assert all(isinstance(entries[knowledge_id].delivery_text, str) for knowledge_id in PHONE_KNOWLEDGE)
    assert all(entries[knowledge_id].delivery_text.strip() for knowledge_id in PHONE_KNOWLEDGE)


def test_the_text_variants_establish_the_text_fact_and_nothing_about_the_card():
    entries = _knowledge()
    assert {operation.fact_id for operation in entries["k_sl_1a_j_r1"].establishes} == {"michelle_text_read"}
    assert {operation.fact_id for operation in entries["k_sl_1a_j_r2"].establishes} == {
        "michelle_text_read",
        "reyes_watched_text",
    }
    assert {operation.fact_id for operation in entries["k_sl_1a_j_r3"].establishes} == {"kristin_calls_read"}
    protected = {
        "memory_card_recovered",
        "continuity_initiative_known",
        "michelle_warning_known",
        "michelle_lead_actionable",
    }
    assert not protected & {
        operation.fact_id for knowledge_id in PHONE_KNOWLEDGE for operation in entries[knowledge_id].establishes
    }


def test_the_phone_thread_leaks_no_protected_material():
    protected = (
        "memory card",
        "recording",
        "janus",
        "brandon",
        "dead drop",
        "continuity initiative",
        "removable media",
    )
    for knowledge_id in PHONE_KNOWLEDGE:
        delivery = _knowledge()[knowledge_id].delivery_text.lower()
        assert not any(term in delivery for term in protected)


def test_the_officer_text_is_not_voiceable():
    entries = _knowledge()
    for knowledge_id in PHONE_KNOWLEDGE:
        entry = entries[knowledge_id]
        assert entry.voiceable is False
        assert "michelle_phone" in entry.reach_entity_ids
