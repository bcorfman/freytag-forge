from __future__ import annotations

from random import Random

import pytest

from storygame.cli import run_replay
from storygame.engine.world import build_default_state
from storygame.evaluation import (
    FAILURE_CATEGORIES,
    classify_structured_artifact,
    load_evaluation_adapter_revisions,
    load_evaluation_fixtures,
    summarize_adapter_measurements,
)
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from tests.narrator_stubs import StubNarrator


def test_phase_zero_fixtures_cover_four_distinct_vertical_slices():
    fixtures = load_evaluation_fixtures()
    revisions = load_evaluation_adapter_revisions()

    assert {fixture["id"] for fixture in fixtures} == {
        "mystery-investigation",
        "fantasy-journey",
        "sci-fi-technical-crisis",
        "relationship-social-scene",
    }
    assert {fixture["genre"] for fixture in fixtures} == {"mystery", "fantasy", "sci-fi", "romance"}
    assert all(fixture["model"] == "phase0-deterministic-stub-v1" for fixture in fixtures)
    assert all(fixture["prompt_version"] == "phase0-fixture-contract-v1" for fixture in fixtures)
    assert all(fixture["generation_settings"]["temperature"] == 0 for fixture in fixtures)
    assert revisions == {
        "cloudflare_workers_ai": "cloudflare-workers-ai-v1",
    }


@pytest.mark.parametrize("fixture", load_evaluation_fixtures(), ids=lambda fixture: fixture["id"])
def test_phase_zero_fixture_initializes_saves_loads_and_replays_deterministically(fixture, tmp_path):
    initial_state = build_default_state(
        seed=fixture["seed"],
        genre=fixture["genre"],
        session_length=fixture["session_length"],
        tone=fixture["tone"],
    )
    with SqliteSaveStore(tmp_path / f"{fixture['id']}.sqlite") as store:
        store.save_run(fixture["id"], initial_state, Random(fixture["seed"]))
        loaded_state, loaded_rng = store.load_run(fixture["id"])

    assert loaded_state.replay_signature() == initial_state.replay_signature()
    assert loaded_rng.getstate() == Random(fixture["seed"]).getstate()

    first_replay = run_replay(
        fixture["seed"],
        fixture["commands"],
        genre=fixture["genre"],
        session_length=fixture["session_length"],
        tone=fixture["tone"],
        narrator=StubNarrator("A measured response keeps the scene grounded."),
    )
    second_replay = run_replay(
        fixture["seed"],
        fixture["commands"],
        genre=fixture["genre"],
        session_length=fixture["session_length"],
        tone=fixture["tone"],
        narrator=StubNarrator("A measured response keeps the scene grounded."),
    )

    assert first_replay.replay_signature() == second_replay.replay_signature()


@pytest.mark.parametrize("category", FAILURE_CATEGORIES)
def test_structured_evaluation_classifies_each_failure_category(category):
    artifact = {
        "invariant_violations": [category] if category == "contradiction" else [],
        "action_outcome": "impossible" if category == "impossible_action" else "accepted",
        "knowledge_leaks": ["hidden clue"] if category == "hidden_information_leak" else [],
        "role_violations": ["wrong speaker"] if category == "role_drift" else [],
        "causal_gaps": ["missing consequence"] if category == "causal_omission" else [],
        "committed_claims": [],
        "rendered_claims": ["new fact"] if category == "uncommitted_narration" else [],
        "scene_pressure": ["steady", "steady", "steady"] if category == "repetitive_scene_pressure" else [],
        "agency_outcome": "blocked" if category == "blocked_player_agency" else "accepted",
        "clarification_requested": False,
        "provider_recovery": {"exhausted": True} if category == "exhausted_provider_recovery" else {},
    }

    assert classify_structured_artifact(artifact) == (category,)


def test_structured_evaluation_classifies_exhausted_provider_recovery():
    artifact = {"provider_recovery": {"attempts": 2, "budget": 2, "exhausted": True}}

    assert classify_structured_artifact(artifact) == ("exhausted_provider_recovery",)


def test_adapter_measurements_report_every_required_baseline_without_creating_a_release_gate():
    report = summarize_adapter_measurements(
        (
            {
                "adapter": "cloudflare_workers_ai",
                "revision": "fixture-cloudflare-v1",
                "proposal_valid": True,
                "directly_accepted": True,
                "repaired": False,
                "repair_succeeded": False,
                "failure_categories": (),
                "latency_ms": 120,
                "input_tokens": 80,
                "output_tokens": 20,
            },
            {
                "adapter": "cloudflare_workers_ai",
                "revision": "fixture-cloudflare-v1",
                "proposal_valid": False,
                "directly_accepted": False,
                "repaired": True,
                "repair_succeeded": True,
                "failure_categories": ("role_drift",),
                "latency_ms": 180,
                "input_tokens": 90,
                "output_tokens": 30,
            },
        ),
        required_adapters=("cloudflare_workers_ai",),
    )

    assert report["kind"] == "informational_baseline"
    assert report["missing_adapters"] == ()
    assert report["adapters"]["cloudflare_workers_ai"] == {
        "revision": "fixture-cloudflare-v1",
        "turns": 2,
        "proposal_validity": 0.5,
        "direct_acceptance": 0.5,
        "bounded_repair_success": 1.0,
        "hidden_information_leaks": 0,
        "role_drift": 1,
        "latency_ms": 150.0,
        "input_tokens": 170,
        "output_tokens": 50,
    }
