from __future__ import annotations

from random import Random

from storygame.engine.affordances import build_affordance_context
from storygame.engine.bootstrap import validate_bootstrap_plan
from storygame.engine.consequences import apply_consequences
from storygame.engine.fact_commit import ValidatedFactCommitter
from storygame.engine.turn_runtime import execute_turn_proposal
from storygame.engine.world import build_state_from_bootstrap_plan
from storygame.llm.bootstrap_contracts import parse_bootstrap_plan
from storygame.llm.contracts import parse_turn_proposal


def _state():
    plan = parse_bootstrap_plan(
        {
            "outline_id": "phase4_fixture",
            "protagonist_id": "player",
            "locations": [
                {"id": "lab", "name": "Lab", "description": "A bright lab.", "exits": {"east": "hall"}, "traits": []},
                {"id": "hall", "name": "Hall", "description": "A quiet hall.", "exits": {"west": "lab"}, "traits": []},
            ],
            "characters": [
                {
                    "id": "player",
                    "name": "Player",
                    "description": "The player.",
                    "role": "protagonist",
                    "stable_traits": [],
                    "dynamic_traits": [],
                    "location_id": "lab",
                    "inventory": ["passkey"],
                },
                {
                    "id": "rival",
                    "name": "Rival",
                    "description": "A rival.",
                    "role": "rival",
                    "stable_traits": [],
                    "dynamic_traits": [],
                    "location_id": "lab",
                    "inventory": [],
                },
            ],
            "items": [
                {
                    "id": "passkey",
                    "name": "Passkey",
                    "description": "A key.",
                    "kind": "tool",
                    "stable_traits": [],
                    "dynamic_traits": [],
                    "location_id": "",
                    "holder_id": "player",
                    "portable": True,
                },
                {
                    "id": "sample",
                    "name": "Sample",
                    "description": "A sample.",
                    "kind": "clue",
                    "stable_traits": [],
                    "dynamic_traits": [],
                    "location_id": "lab",
                    "holder_id": "",
                    "portable": True,
                },
            ],
            "goals": [{"goal_id": "open_hall", "summary": "Open the hall.", "kind": "primary", "status": "active"}],
            "triggers": [],
        }
    )
    validate_bootstrap_plan(plan)
    state = build_state_from_bootstrap_plan(seed=4, plan=plan)
    ValidatedFactCommitter().commit(
        state,
        [
            {"op": "assert", "fact": ("locked", "east", "lab", "passkey")},
            {"op": "assert", "fact": ("npc_relationship", "rival", "player", "hostile")},
            {"op": "assert", "fact": ("weather", "lab", "rain")},
            {"op": "assert", "fact": ("trace", "sample", "lab", "wet")},
            {"op": "assert", "fact": ("sensory_propagation", "lab", "hall", "air")},
        ],
        source="test",
    )
    return state


def test_consequence_rules_commit_access_social_and_environmental_facts() -> None:
    state = _state()

    report = apply_consequences(state)

    assert state.world_facts.holds("social_stance", "rival", "player", "guarded")
    assert state.world_facts.holds("trace", "sample", "hall", "wet")
    assert not state.world_facts.holds("locked", "east", "lab", "passkey")
    assert report["applied_rule_ids"]


def test_consequences_are_deterministic_and_do_not_reapply_numeric_effects() -> None:
    first = _state()
    second = _state()

    first_report = apply_consequences(first)
    second_report = apply_consequences(second)

    assert first_report == second_report
    assert first.world_facts.all() == second.world_facts.all()
    assert first.fact_metrics == second.fact_metrics


def test_turn_runtime_runs_consequences_before_triggers() -> None:
    state = _state()
    proposal = parse_turn_proposal(
        {
            "turn_id": "phase4-turn",
            "intent": "take",
            "narration": "You lift the sample.",
            "dialogue_lines": [],
            "semantic_actions": [
                {
                    "action_id": "take",
                    "action_type": "take_item",
                    "actor_id": "player",
                    "target_id": "",
                    "item_id": "sample",
                    "location_id": "lab",
                }
            ],
            "state_delta": {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
        }
    )

    result = execute_turn_proposal(state, proposal, Random(1))

    assert result["state"].world_facts.holds("discovered_clue", "sample")
    consequence_index = next(i for i, event in enumerate(result["events"]) if event.type == "consequence")
    trigger_indexes = [i for i, event in enumerate(result["events"]) if event.type == "trigger"]
    assert not trigger_indexes or consequence_index < min(trigger_indexes)


def test_affordances_are_derived_from_current_facts() -> None:
    state = _state()

    affordances = build_affordance_context(state)

    assert affordances["location_id"] == "lab"
    assert affordances["exits"] == ({"destination": "hall", "locked": False},)
    assert affordances["items"] == ({"id": "sample", "portable": True},)
    assert affordances["npcs"] == ({"id": "rival", "can_address": True},)


def test_npc_affordances_use_fact_backed_location_and_handle_an_unknown_npc() -> None:
    state = _state()

    assert build_affordance_context(state, observer="rival")["location_id"] == "lab"
    assert build_affordance_context(state, observer="unknown")["location_id"] == ""
