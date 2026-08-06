from __future__ import annotations

import pytest

from storygame.engine.interfaces import load_policy_bundle
from storygame.engine.policies import (
    PredicatePolicyRegistry,
    intent_policy,
    normalize_intent_family,
    resolve_visible_aliases,
    validate_proposed_fact_ops,
)
from storygame.engine.world import build_default_state


def test_policy_bundle_declares_all_phase_two_families() -> None:
    bundle = load_policy_bundle("mystery")
    families = {entry["family"] for entry in bundle["predicates"]}

    assert {
        "world",
        "perception",
        "knowledge",
        "relationships",
        "tasks",
        "traces",
        "dramatic",
    } <= families
    assert bundle["rules"]


def test_proposal_policy_rejects_unknown_predicates_without_mutating_state() -> None:
    state = build_default_state(seed=410, genre="mystery")
    registry = PredicatePolicyRegistry.for_genre("mystery")

    with pytest.raises(ValueError, match="unauthorized predicate"):
        validate_proposed_fact_ops(
            state,
            [{"op": "assert", "fact": ("secret_truth", "villain") }],
            registry=registry,
        )

    assert not state.world_facts.holds("secret_truth", "villain")


def test_proposal_policy_normalizes_fact_terms_and_allows_bounded_facts() -> None:
    registry = PredicatePolicyRegistry.for_genre("mystery")
    normalized = validate_proposed_fact_ops(
        None,
        [
            {"op": "assert", "fact": ("flag", "player", "  saw_key  ")},
            {"op": "assert", "fact": ("knows", "player", "ledger_page")},
        ],
        registry=registry,
    )

    assert normalized == (
        {"op": "assert", "fact": ("flag", "player", "saw_key")},
        {"op": "assert", "fact": ("knows", "player", "ledger_page")},
    )


def test_rule_conflicts_fail_deterministically_before_play() -> None:
    registry = PredicatePolicyRegistry.for_genre("mystery")
    assert registry.rule_ids == tuple(sorted(registry.rule_ids))
    assert len(registry.rule_ids) == len(set(registry.rule_ids))


def test_intent_families_are_extensible_and_not_parser_commands() -> None:
    assert normalize_intent_family("go") == "movement"
    assert normalize_intent_family("inspect") == "examination"
    assert normalize_intent_family("talk") == "communication"
    assert normalize_intent_family("hide the evidence") == "concealment"
    assert normalize_intent_family("wait") == "waiting"


def test_visible_alias_resolution_returns_ambiguity_instead_of_guessing() -> None:
    state = build_default_state(seed=411, genre="mystery")
    room_id = state.player.location
    state.world_facts.assert_fact("room_item", room_id, "case_file")
    state.world_facts.assert_fact("room_item", room_id, "ledger_page")
    state.world.items["case_file"].name = "Evidence"
    state.world.items["ledger_page"].name = "Evidence"

    assert resolve_visible_aliases(state, "evidence") == ("case_file", "ledger_page")


def test_policy_rejects_invalid_operation_and_arity() -> None:
    registry = PredicatePolicyRegistry.for_genre("mystery")
    with pytest.raises(ValueError, match="rejects operation"):
        validate_proposed_fact_ops(None, [{"op": "numeric_delta", "fact": ()}], registry=registry)
    with pytest.raises(ValueError, match="expects"):
        registry.validate(("flag", "player"))


def test_policy_normalizes_identifiers_and_handles_unknown_intents() -> None:
    registry = PredicatePolicyRegistry.for_genre("mystery")
    policy = registry.get("flag")
    assert policy is not None
    assert registry._normalize("Saw Key!", "identifier") == "saw_key"
    assert normalize_intent_family("invent a completely new move") == "manipulation"
    assert intent_policy("waiting").bounded_effects == ("advance_time",)
    with pytest.raises(ValueError, match="Unknown intent"):
        intent_policy("unknown")


def test_visible_alias_resolution_handles_empty_and_npc_queries() -> None:
    state = build_default_state(seed=412, genre="mystery")
    assert resolve_visible_aliases(state, "", kind="item") == ()
    npc_ids = resolve_visible_aliases(state, "daria", kind="npc")
    assert npc_ids == ("daria_stone",)
