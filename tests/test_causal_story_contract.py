"""Phase-1 causal authoring contracts stay local and genre-agnostic."""

# ruff: noqa: E501

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from storygame.authoring.causal_contracts import CausalValidationError, validate_causal_compiled_story
from storygame.authoring.causal_critics import (
    CausalCompletenessCritic,
    FreytagProgressionCritic,
    RouteFairnessCritic,
)
from storygame.authoring.causal_profiles import CausalProfileRegistry


def _story() -> dict[str, object]:
    return {
        "schema_version": "story-blueprint-v2",
        "id": "signal_crisis",
        "version": 1,
        "provenance": {"source_format": "story-outline-inventory-v1", "source_id": "signal", "source_hash": "a" * 64},
        "genre": "sci-fi",
        "profile": "sci-fi",
        "title": "Signal Crisis",
        "premise": "A crew must repair a failing beacon before the evacuation window closes.",
        "opening_truth_ids": ["opening"],
        "truths": [
            {"id": "opening", "summary": "The beacon is failing."},
            {"id": "failure", "summary": "The cause is known.", "roles": ["failure_cause"]},
            {"id": "constraint", "summary": "The constraint is known.", "roles": ["constraint"]},
            {"id": "remedy", "summary": "A remedy is known.", "roles": ["remedy"]},
            {"id": "tradeoff", "summary": "The trade-off is accepted.", "roles": ["trade_off"]},
        ],
        "participants": [{"id": "engineer", "role": "crew"}],
        "locations": [{"id": "dock", "role": "opening", "initial_access": True}, {"id": "relay", "role": "service"}],
        "connected_routes": [
            {"id": "dock_relay", "from_location_id": "dock", "to_location_id": "relay", "aliases": ["service lift"]}
        ],
        "causal_events": [
            {
                "id": "failure_event",
                "actor_ids": ["engineer"],
                "location_id": "dock",
                "output_truths": ["failure", "constraint"],
                "earliest": 1,
                "latest": 2,
            },
            {
                "id": "repair_event",
                "actor_ids": ["engineer"],
                "location_id": "relay",
                "input_truths": ["failure"],
                "output_truths": ["remedy", "tradeoff"],
                "earliest": 3,
                "latest": 4,
                "prerequisite_event_ids": ["failure_event"],
            },
        ],
        "timeline_constraints": [{"before_event_id": "failure_event", "after_event_id": "repair_event"}],
        "evidence_opportunities": [
            {
                "id": "scan",
                "truth_id": "failure",
                "kind": "scan",
                "holder_id": "engineer",
                "location_id": "dock",
                "route_id": "diagnose_scan",
            },
            {
                "id": "log",
                "truth_id": "failure",
                "kind": "log",
                "holder_id": "engineer",
                "location_id": "relay",
                "route_id": "diagnose_log",
            },
            {
                "id": "repair_log",
                "truth_id": "tradeoff",
                "kind": "log",
                "holder_id": "engineer",
                "location_id": "relay",
                "route_id": "commit",
            },
            {
                "id": "crew_testimony",
                "truth_id": "tradeoff",
                "kind": "testimony",
                "holder_id": "engineer",
                "location_id": "relay",
                "route_id": "commit_testimony",
            },
        ],
        "party_knowledge": [{"participant_id": "engineer", "truth_ids": ["opening"]}],
        "knowledge_protections": [{"truth_id": "tradeoff", "release_after_revelation_ids": ["commit"]}],
        "revelations": [
            {"id": "diagnose", "truth_id": "failure", "gate_beat_ids": ["setup"]},
            {"id": "commit", "truth_id": "tradeoff", "gate_beat_ids": ["crisis"]},
        ],
        "realization_routes": [
            {
                "id": "diagnose_scan",
                "revelation_id": "diagnose",
                "opportunity_ids": ["scan"],
                "result_truth_ids": ["failure"],
                "failure_forward": {"consequence_truth_ids": ["failure"], "alternative_route_ids": ["diagnose_log"]},
            },
            {
                "id": "diagnose_log",
                "revelation_id": "diagnose",
                "opportunity_ids": ["log"],
                "result_truth_ids": ["failure"],
                "failure_forward": {"consequence_truth_ids": ["failure"], "alternative_route_ids": ["diagnose_scan"]},
            },
            {
                "id": "commit",
                "revelation_id": "commit",
                "opportunity_ids": ["repair_log"],
                "prerequisite_revelation_ids": ["diagnose"],
                "result_truth_ids": ["tradeoff"],
                "failure_forward": {"consequence_truth_ids": ["tradeoff"]},
            },
            {
                "id": "commit_testimony",
                "revelation_id": "commit",
                "opportunity_ids": ["crew_testimony"],
                "prerequisite_revelation_ids": ["diagnose"],
                "result_truth_ids": ["tradeoff"],
                "failure_forward": {"consequence_truth_ids": ["tradeoff"]},
            },
        ],
        "required_outcomes": [{"id": "survive", "truth_id": "tradeoff"}],
        "required_beats": [
            {"id": "setup", "phase": "setup", "pressure": 0},
            {"id": "rise", "phase": "rising_action", "pressure": 1, "prerequisite_revelation_ids": ["diagnose"]},
            {"id": "crisis", "phase": "crisis", "pressure": 2, "prerequisite_revelation_ids": ["diagnose"]},
            {"id": "climax", "phase": "climax", "pressure": 3, "prerequisite_revelation_ids": ["commit"]},
            {
                "id": "resolution",
                "phase": "resolution",
                "required_outcome_id": "survive",
                "pressure": 4,
                "prerequisite_revelation_ids": ["commit"],
            },
        ],
        "optional_beats": [
            {"id": "bond", "phase": "rising_action", "pressure": 1, "purpose": "relationship_development"}
        ],
        "end_states": [{"id": "ending", "required_outcome_ids": ["survive"], "required_truth_ids": ["tradeoff"]}],
    }


def _profiles() -> CausalProfileRegistry:
    return CausalProfileRegistry.from_directory(Path("data/genre_profiles"))


def test_phase_one_contract_validates_topology_causality_knowledge_and_freytag() -> None:
    story = validate_causal_compiled_story(_story())
    profiles = _profiles()

    assert profiles.validate(story) is story
    assert CausalCompletenessCritic().critique(story).accepted
    assert RouteFairnessCritic(profiles).critique(story).accepted
    assert FreytagProgressionCritic(profiles).critique(story).accepted


@pytest.mark.parametrize("genre", ["mystery", "fantasy", "sci-fi", "relationship"])
def test_data_driven_profiles_validate_the_same_generic_contract(genre: str) -> None:
    payload = _story()
    profiles = _profiles()
    profile = profiles.resolve(genre)
    payload["genre"] = genre
    payload["profile"] = genre
    roles = [item.role for item in (*profile.terminal_roles, *profile.causal_roles)]
    for truth in payload["truths"]:
        truth["roles"] = roles
    for index, opportunity in enumerate(payload["evidence_opportunities"]):
        opportunity["kind"] = profile.allowed_opportunity_types[index % len(profile.allowed_opportunity_types)]

    assert profiles.validate(validate_causal_compiled_story(payload)).genre == genre


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda value: value["causal_events"][1].update(prerequisite_event_ids=["repair_event"]), "CAUSAL_CYCLE"),
        (lambda value: value["causal_events"][1].update(earliest=1, latest=1), "TIMELINE_INVALID"),
        (lambda value: value["evidence_opportunities"][0].update(location_id="missing"), "UNKNOWN_REFERENCE"),
        (lambda value: value["evidence_opportunities"][1].update(location_id="isolated"), "UNKNOWN_REFERENCE"),
        (lambda value: value["party_knowledge"][0].update(truth_ids=["tradeoff"]), "PREMATURE_PROTECTED_KNOWLEDGE"),
        (
            lambda value: value["optional_beats"][0].update(
                purpose="alternative_satisfier", required_outcome_id="missing"
            ),
            "UNKNOWN_REFERENCE",
        ),
        (
            lambda value: value["realization_routes"][2].update(failure_forward={"consequence_truth_ids": ["remedy"]}),
            "FAILURE_FORWARD_DEAD_END",
        ),
    ],
)
def test_phase_one_contract_rejects_invalid_causal_dependencies(mutate, code: str) -> None:
    payload = deepcopy(_story())
    mutate(payload)

    with pytest.raises(CausalValidationError, match=code):
        validate_causal_compiled_story(payload)


def test_phase_one_contract_rejects_an_unreachable_required_opportunity() -> None:
    payload = _story()
    payload["locations"].append({"id": "sealed", "role": "sealed"})
    payload["evidence_opportunities"][0]["location_id"] = "sealed"

    with pytest.raises(CausalValidationError, match="LOCATION_UNREACHABLE"):
        validate_causal_compiled_story(payload)


def test_critics_reject_single_route_proof_and_missing_terminal_chain() -> None:
    payload = _story()
    payload["realization_routes"] = [item for item in payload["realization_routes"] if item["id"] != "diagnose_scan"]
    payload["evidence_opportunities"] = [item for item in payload["evidence_opportunities"] if item["id"] != "scan"]
    payload["realization_routes"][0]["failure_forward"].pop("alternative_route_ids")
    payload["causal_events"][1]["output_truths"] = ["remedy"]
    story = validate_causal_compiled_story(payload)

    assert not RouteFairnessCritic(_profiles()).critique(story).accepted
    assert not CausalCompletenessCritic().critique(story).accepted
