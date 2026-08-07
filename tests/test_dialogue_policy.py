from __future__ import annotations

from storygame.engine.dialogue_policy import _normalized_appearance_phrase, dialogue_fact_conflict
from tests.fast_fixtures import make_cached_story_state as build_default_state


def test_dialogue_policy_rejects_conflicting_committed_appearance() -> None:
    state = build_default_state(seed=515, genre="mystery")
    committed = state.world_facts.query("npc_appearance", "daria_stone", None)[0][2]

    assert dialogue_fact_conflict(state, "daria_stone", "I'm wearing a simple dark dress.", "appearance")
    assert not dialogue_fact_conflict(state, "daria_stone", f"I'm wearing {committed}.", "appearance")
    assert not dialogue_fact_conflict(state, "daria_stone", "I'm wearing a dark coat.", "ledger")


def test_dialogue_policy_ignores_non_appearance_and_uncommitted_speakers() -> None:
    state = build_default_state(seed=516, genre="mystery")
    for committed in state.world_facts.query("npc_appearance", "daria_stone", None):
        state.world_facts.retract_fact(*committed)

    assert not dialogue_fact_conflict(state, "", "I'm wearing a dark coat.", "appearance")
    assert not dialogue_fact_conflict(state, "unknown", "I'm wearing a dark coat.", "appearance")
    assert not dialogue_fact_conflict(state, "daria_stone", "The case is getting stranger.", "appearance")
    assert not dialogue_fact_conflict(state, "daria_stone", "I'm wearing a dark coat.", "appearance")


def test_appearance_normalization_handles_quotes_articles_and_empty_text() -> None:
    assert _normalized_appearance_phrase("I'm wearing the crisp white blouse.") == "a crisp white blouse"
    assert _normalized_appearance_phrase("I am wearing 'an old coat'.") == "an old coat"
    assert _normalized_appearance_phrase("I am wearing   ") == ""
    assert _normalized_appearance_phrase("I am wearing .") == ""
    assert _normalized_appearance_phrase("The room feels colder now.") == ""
