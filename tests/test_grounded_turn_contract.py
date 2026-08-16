from __future__ import annotations

import json
from random import Random

import pytest

from storygame.engine.environment import apply_environment_transition, resolve_environment_complication
from storygame.engine.freeform import LlmFreeformProposalAdapter, resolve_freeform_roleplay
from storygame.engine.semantic_actions import commit_semantic_action
from storygame.engine.staging_claims import validate_staging_claims
from storygame.engine.world_builder import WorldPackageValidationError, build_world_package, validate_world_package
from storygame.persistence.savegame_sqlite import SqliteSaveStore
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


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "romance"))
def test_relation_family_matrix_is_valid_across_genres_and_rejects_adversarial_claims(genre: str) -> None:
    state = build_default_state(seed=909, genre=genre)
    location_id = next(fact[2] for fact in state.world_facts.query("at", "player", None))
    environment = next(fact for fact in state.world_facts.query("environment", location_id, None))
    access = next(fact for fact in state.world_facts.query("path") if location_id in fact[2:])
    state.world_facts.assert_fact("event", "phase4_marker", location_id)
    claims = (
        {"relation": "custody", "subject_id": "field_kit", "target_id": "player", "location_id": "", "state_id": ""},
        {
            "relation": "environment",
            "subject_id": "",
            "target_id": "",
            "location_id": location_id,
            "state_id": environment[2],
        },
        {
            "relation": "access",
            "subject_id": access[1],
            "target_id": "",
            "location_id": location_id,
            "state_id": "available",
        },
        {
            "relation": "event",
            "subject_id": "phase4_marker",
            "target_id": "",
            "location_id": location_id,
            "state_id": "",
        },
    )

    validate_staging_claims(state, claims)
    for claim in claims:
        adversarial = {**claim, "state_id": "fabricated"}
        if claim["relation"] == "custody":
            adversarial["target_id"] = "fabricated"
        elif claim["relation"] == "event":
            adversarial["subject_id"] = "fabricated"
        with pytest.raises(ValueError, match="STAGING_CLAIM"):
            validate_staging_claims(state, (adversarial,))


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


def test_accepted_turn_projects_request_retry_latency_and_fact_evidence(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
        "storygame.engine.freeform._story_agent_chat_complete", lambda *_args: json.dumps(next(responses))
    )

    result = resolve_freeform_roleplay(state, "inspect the scene", LlmFreeformProposalAdapter())
    trace = result["event"].metadata["staging_trace"]

    assert trace["outcome"] == "accepted"
    assert trace["retries"] == 1
    assert len(trace["request_ids"]) == 2
    assert trace["attempts"][0]["status"] == "rejected"
    assert trace["attempts"][1]["status"] == "accepted"
    assert trace["latency_ms"] >= 0

    store = SqliteSaveStore(tmp_path / "saves.sqlite")
    try:
        store.save_run("phase4", result["state"], Random(907), raw_command="inspect the scene")
        artifact = json.loads((store.artifacts_root / "phase4" / "StoryState.json").read_text(encoding="utf-8"))
    finally:
        store.close()
    persisted_trace = artifact["trace"]["grounded_turn_staging"]
    assert persisted_trace["request_ids"] == list(trace["request_ids"])
    assert persisted_trace["retries"] == trace["retries"]
    assert persisted_trace["outcome"] == "accepted"


def test_typed_claim_parity_replaces_phrase_based_custody_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    state = build_default_state(seed=907, genre="mystery")
    calls = 0

    def _reply(*_args: object) -> str:
        nonlocal calls
        calls += 1
        return __import__("json").dumps(
            {
                "dialog_proposal": {
                    "speaker": "narrator",
                    "text": "The case file rests on the ground beside Daria.",
                    "tone": "in_world",
                },
                "action_proposal": {
                    "intent": "inspect",
                    "targets": [],
                    "arguments": {},
                    "proposed_effects": [],
                },
                "staging_claims": [
                    {
                        "relation": "custody",
                        "subject_id": "case_file",
                        "target_id": "daria_stone",
                        "location_id": "",
                        "state_id": "",
                    }
                ],
            }
        )

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _reply)

    result = resolve_freeform_roleplay(state, "inspect the scene", LlmFreeformProposalAdapter())

    assert calls == 1
    assert result["state"].turn_index == state.turn_index + 1
    assert result["accepted_prose"] == "The case file rests on the ground beside Daria."


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
