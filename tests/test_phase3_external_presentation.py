import json

from storygame.engine.freeform import _freeform_planner_prompt
from storygame.engine.perception import observer_context_slice
from storygame.llm.prompts import SYSTEM_CONSTRAINTS
from storygame.llm.story_agents.agents import _opening_facts_seed
from storygame.llm.story_agents.prompts import (
    build_narrator_opening_prompt,
    build_story_architect_prompt,
    build_story_bootstrap_prompt,
)
from tests.fast_fixtures import make_cached_story_state as build_default_state


def test_opening_briefing_is_an_explicit_player_knowledge_grant() -> None:
    state = build_default_state(seed=803, genre="mystery")

    assert state.world_facts.holds("knows", "player", "victim_name")
    assert state.world_facts.holds("knows", "player", "strongest_lead")


def test_opening_facts_and_planner_exclude_unpermitted_case_truth() -> None:
    state = build_default_state(seed=804, genre="mystery")
    state.world_facts.assert_fact("case_fact", "sealed_record", "A protected fact.")
    state.world_facts.assert_fact("knows", "olivia_thompson", "sealed_record")

    opening_facts = _opening_facts_seed(state)
    _system, payload = _freeform_planner_prompt(state, "Ask Daria Stone about the record")

    assert all(entry["key"] != "sealed_record" for entry in opening_facts["situation_facts"])
    assert "A protected fact." not in payload
    assert ("case_fact", "sealed_record", "A protected fact.") not in observer_context_slice(state, "player")


def test_addressed_npc_receives_only_its_own_private_context() -> None:
    state = build_default_state(seed=805, genre="mystery")
    state.world_facts.assert_fact("case_fact", "daria_only", "Daria's private conclusion.")
    state.world_facts.assert_fact("knows", "daria_stone", "daria_only")
    state.world_facts.assert_fact("case_fact", "other_only", "Another person's private conclusion.")
    state.world_facts.assert_fact("knows", "olivia_thompson", "other_only")

    _system, payload = _freeform_planner_prompt(state, "Daria Stone, what have you concluded?")
    context = json.loads(payload)["addressed_npc_context"]
    serialized = json.dumps(context)

    assert "Daria's private conclusion." in serialized
    assert "Another person's private conclusion." not in serialized


def test_shared_presentation_prompts_are_roleplay_forward_and_story_agnostic() -> None:
    bootstrap_system, _ = build_story_bootstrap_prompt(
        "premise", "fantasy", "tense", "short", [], [], {}, [], [], [], {}
    )
    architect_system, _ = build_story_architect_prompt("premise", "name", "fantasy", "tense")
    narrator_system, _ = build_narrator_opening_prompt("draft", {})

    for prompt in (bootstrap_system, architect_system, narrator_system):
        assert "mystery stories" not in prompt.lower()
        assert "named male detective" not in prompt.lower()
    assert "active person" in narrator_system
    shared_policy = " ".join(SYSTEM_CONSTRAINTS).lower()
    assert "grounded roleplay, not a status report" in shared_policy
    assert "never introduce a fact, protected knowledge, event, or visible state change" in shared_policy
