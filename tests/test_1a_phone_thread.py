from __future__ import annotations

from pathlib import Path

import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(ROOT)
PHONE_REALIZATIONS = ("SL-1A-J-R1", "SL-1A-J-R2", "SL-1A-J-R3")
PHONE_KNOWLEDGE = ("k_sl_1a_j_r1", "k_sl_1a_j_r2", "k_sl_1a_j_r3")
TEXT = (
    "Kristin enters Michelle's passcode, the one she has known for years, and the phone opens on a single text "
    'from Michelle, sent at 4:07am: "Come to the house. Don\'t call."'
)
UNEASY_TEXT = (
    TEXT + " Officer Reyes lowers his printed list. His eyes stay on the phone in her hand, and when she looks up he "
    "glances away a moment too slowly. Kristin turns the screen toward herself, uneasy."
)
CALLS_TEXT = (
    "Below the text, Kristin's own calls to Michelle fill the log, one after another, and none of them were answered."
)


def _knowledge() -> dict[str, object]:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _routes() -> dict:
    data = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["storylets"]}


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
    assert storylet["scene_id"] == "1A"
    assert [option["id"] for option in storylet["realization_options"]] == list(PHONE_REALIZATIONS)
    pacing = storylet["activation"]["pacing"]
    assert (pacing["earliest_turn"], pacing["target_turn"], pacing["latest_turn"]) == (0, 5, 11)


def test_phone_thread_facts_are_declared_everywhere():
    fact_ids = {"michelle_text_read", "kristin_calls_read"}
    routes = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    assert fact_ids <= {fact.id for fact in PACKAGE.knowledge.facts}
    assert fact_ids <= set(PACKAGE.world.facts)
    assert fact_ids <= {fact["id"] for fact in routes["new_fact_ids"]}


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
    assert entries["k_sl_1a_j_r1"].delivery_text == TEXT
    assert entries["k_sl_1a_j_r2"].delivery_text == UNEASY_TEXT
    assert entries["k_sl_1a_j_r3"].delivery_text == CALLS_TEXT


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
