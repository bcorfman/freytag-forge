from __future__ import annotations

import pytest

from storygame.engine.environment import apply_environment_transition, resolve_environment_complication
from storygame.engine.freeform import LlmFreeformProposalAdapter, resolve_freeform_roleplay
from storygame.engine.semantic_actions import commit_semantic_action
from storygame.engine.staging_claims import validate_staging_claims
from storygame.engine.world_builder import WorldPackageValidationError, build_world_package, validate_world_package
from tests.fast_fixtures import make_cached_story_state as build_default_state


def test_candidate_claims_cover_each_generic_relation() -> None:
    state = build_default_state(seed=907, genre="mystery")
    state.world_facts.assert_fact("event", "arrival", "front_steps")

    validate_staging_claims(
        state,
        (
            {
                "relation": "custody",
                "subject_id": "case_file",
                "target_id": "daria_stone",
                "location_id": "",
                "state_id": "",
            },
            {
                "relation": "environment",
                "subject_id": "",
                "target_id": "",
                "location_id": "front_steps",
                "state_id": "outdoor",
            },
            {
                "relation": "access",
                "subject_id": "mansion_entrance",
                "target_id": "",
                "location_id": "front_steps",
                "state_id": "available",
            },
            {
                "relation": "event",
                "subject_id": "arrival",
                "target_id": "",
                "location_id": "front_steps",
                "state_id": "",
            },
        ),
    )


@pytest.mark.parametrize(
    "claim",
    (
        {"relation": "custody", "subject_id": "case_file", "target_id": "player", "location_id": "", "state_id": ""},
        {
            "relation": "environment",
            "subject_id": "",
            "target_id": "",
            "location_id": "front_steps",
            "state_id": "blizzard",
        },
        {
            "relation": "access",
            "subject_id": "mansion_entrance",
            "target_id": "",
            "location_id": "front_steps",
            "state_id": "blocked",
        },
        {
            "relation": "event",
            "subject_id": "midnight_crash",
            "target_id": "",
            "location_id": "front_steps",
            "state_id": "",
        },
    ),
)
def test_contradictory_claim_is_rejected(claim: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="STAGING_CLAIM"):
        validate_staging_claims(build_default_state(seed=907, genre="mystery"), (claim,))


def test_duplicate_and_non_visible_claims_are_rejected() -> None:
    state = build_default_state(seed=907, genre="mystery")
    duplicate = {
        "relation": "environment",
        "subject_id": "",
        "target_id": "",
        "location_id": "front_steps",
        "state_id": "outdoor",
    }
    with pytest.raises(ValueError, match="DUPLICATE"):
        validate_staging_claims(state, (duplicate, duplicate))
    with pytest.raises(ValueError, match="NOT_VISIBLE"):
        validate_staging_claims(state, ({**duplicate, "location_id": "foyer"},))


def test_claim_failure_uses_shared_recovery_budget_before_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    state = build_default_state(seed=907, genre="mystery")
    responses = iter(
        (
            {
                "dialog_proposal": {"speaker": "narrator", "text": "The file is yours.", "tone": "in_world"},
                "action_proposal": {"intent": "inspect", "targets": [], "arguments": {}, "proposed_effects": []},
                "staging_claims": [
                    {
                        "relation": "custody",
                        "subject_id": "case_file",
                        "target_id": "player",
                        "location_id": "",
                        "state_id": "",
                    }
                ],
            },
            {
                "dialog_proposal": {"speaker": "narrator", "text": "Daria keeps the file close.", "tone": "in_world"},
                "action_proposal": {"intent": "inspect", "targets": [], "arguments": {}, "proposed_effects": []},
                "staging_claims": [
                    {
                        "relation": "custody",
                        "subject_id": "case_file",
                        "target_id": "daria_stone",
                        "location_id": "",
                        "state_id": "",
                    }
                ],
            },
        )
    )
    monkeypatch.setattr(
        "storygame.engine.freeform._story_agent_chat_complete", lambda *_args: __import__("json").dumps(next(responses))
    )

    result = resolve_freeform_roleplay(state, "inspect the scene", LlmFreeformProposalAdapter())

    assert result["state"].turn_index == state.turn_index + 1


def test_declarative_environment_transition_commits_bounded_consequence() -> None:
    state = build_default_state(seed=913, genre="mystery")
    transition = next(iter(state.world_facts.query("environment_transition")))
    transition_id = transition[1]

    fact_ops = apply_environment_transition(state, transition_id)

    asserted_facts = {tuple(op["fact"]) for op in fact_ops if op["op"] == "assert"}
    assert ("environment", transition[2], transition[4]) in asserted_facts
    assert any(op["fact"][:2] == ("dramatic_consequence", transition_id) for op in fact_ops)


def test_evidence_can_resolve_declared_environment_complication() -> None:
    state = build_default_state(seed=914, genre="fantasy")
    transition_id = next(iter(state.world_facts.query("environment_transition")))[1]
    for op in apply_environment_transition(state, transition_id):
        if op["op"] == "assert":
            state.world_facts.assert_fact(*op["fact"])
        else:
            state.world_facts.retract_fact(*op["fact"])
    evidence_id = next(iter(state.world_facts.query("environment_recovery")))[2]
    state.world_facts.assert_fact("holding", "player", evidence_id)

    fact_ops = resolve_environment_complication(state, transition_id, evidence_id)

    assert {op["op"] for op in fact_ops} == {"retract"}
    assert all(op["fact"][0] in {"route_blocked", "dramatic_consequence"} for op in fact_ops)


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "romance"))
def test_phase_two_environment_declarations_are_viable_across_genres(genre: str) -> None:
    package = build_world_package(genre=genre, session_length="short", seed=915, tone="tense")

    assert validate_world_package(package)["environment_transitions"]


def test_environment_transition_rejects_a_fully_blocked_route_without_evidence() -> None:
    package = build_world_package(genre="mystery", session_length="short", seed=916, tone="tense")
    transition = package["environment_transitions"][0]
    room_id = transition["room_id"]
    transition["blocked_route_ids"] = [path["id"] for path in package["map"]["paths"] if path["from"] == room_id]
    transition["evidence_routes"] = []

    with pytest.raises(WorldPackageValidationError, match="viable"):
        validate_world_package(package)


def test_environment_semantic_actions_use_the_shared_commit_contract() -> None:
    state = build_default_state(seed=917, genre="sci-fi")
    transition_id = next(iter(state.world_facts.query("environment_transition")))[1]
    transition_event = commit_semantic_action(
        state,
        {
            "action_id": "conditions-shift",
            "action_type": "transition_environment",
            "actor_id": "player",
            "target_id": transition_id,
            "item_id": "",
            "location_id": "",
        },
    )
    for operation in transition_event.metadata["fact_ops"]:
        if operation["op"] == "assert":
            state.world_facts.assert_fact(*operation["fact"])
        else:
            state.world_facts.retract_fact(*operation["fact"])
    evidence_id = next(iter(state.world_facts.query("environment_recovery")))[2]
    state.world_facts.assert_fact("holding", "player", evidence_id)

    recovery_event = commit_semantic_action(
        state,
        {
            "action_id": "conditions-recovery",
            "action_type": "resolve_environment",
            "actor_id": "player",
            "target_id": transition_id,
            "item_id": evidence_id,
            "location_id": "",
        },
    )

    assert transition_event.metadata["fact_ops"]
    assert recovery_event.metadata["fact_ops"]


def test_environment_transition_rejects_unknown_or_unheld_recoveries() -> None:
    state = build_default_state(seed=918, genre="romance")
    transition_id = next(iter(state.world_facts.query("environment_transition")))[1]

    with pytest.raises(ValueError, match="Unknown"):
        apply_environment_transition(state, "not_declared")
    with pytest.raises(ValueError, match="requires"):
        resolve_environment_complication(state, transition_id, "not_held")
