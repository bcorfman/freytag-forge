"""Phase-1 causal authoring contracts stay local and genre-agnostic."""

# ruff: noqa: E501

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from storygame.authoring.bound_ir import bind_blueprint
from storygame.authoring.causal_contracts import CausalValidationError, validate_causal_compiled_story
from storygame.authoring.causal_critics import (
    CausalCompletenessCritic,
    FreytagProgressionCritic,
    RouteFairnessCritic,
)
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.symbol_resolution import Namespace, SymbolRegistry


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


def _spatial_story() -> dict[str, object]:
    """A fully declared spatial projection without changing runtime fixtures."""

    payload = _story()
    payload["participants"] = [
        {
            "id": "engineer",
            "role": "crew",
            "public_name": "Iris Vale",
            "public_role": "systems engineer",
            "public_description": "A focused engineer monitoring the failing beacon.",
            "initial_location_id": "dock",
            "initial_availability": "present",
        },
        {
            "id": "navigator",
            "role": "crew",
            "public_name": "Tomas Reed",
            "public_role": "navigation officer",
            "public_description": "A watchful navigator keeping one eye on the clock.",
            "initial_location_id": "dock",
            "initial_availability": "present",
        },
    ]
    payload["movement_plans"] = [
        {
            "id": "engineer_to_relay",
            "participant_id": "engineer",
            "source_location_id": "dock",
            "destination_location_id": "relay",
            "activation_truth_ids": ["opening"],
            "player_may_accompany": True,
        }
    ]
    payload["scene_subjects"] = [
        {
            "id": "dock_console",
            "kind": "structure",
            "location_id": "dock",
            "inspectable": True,
            "public_description": "A diagnostic console flashes a steady warning.",
            "evidence_opportunity_ids": ["scan"],
        }
    ]
    payload["evidence_realizations"] = [
        {
            "id": "scan_console",
            "evidence_opportunity_id": "scan",
            "kind": "scene_evidence",
            "location_id": "dock",
            "custody_holder_id": "engineer",
            "scene_subject_id": "dock_console",
            "public_description": "The console holds a fresh diagnostic scan.",
        },
        {
            "id": "relay_log",
            "evidence_opportunity_id": "log",
            "kind": "document",
            "location_id": "relay",
            "custody_holder_id": "engineer",
            "public_description": "A relay log is available to inspect.",
        },
        {
            "id": "repair_record",
            "evidence_opportunity_id": "repair_log",
            "kind": "document",
            "location_id": "relay",
            "custody_holder_id": "engineer",
            "public_description": "A repair record is available to inspect.",
        },
        {
            "id": "crew_testimony_realization",
            "evidence_opportunity_id": "crew_testimony",
            "kind": "testimony",
            "location_id": "relay",
            "custody_holder_id": "engineer",
            "public_description": "The engineer can discuss the crew's decision.",
        },
    ]
    payload["group_encounters"] = [
        {
            "id": "dock_watch",
            "location_id": "dock",
            "label": "the bridge crew",
            "participant_ids": ["engineer", "navigator"],
            "introduction_truth_ids": ["opening"],
        }
    ]
    payload["opening"] = {
        "scene": "The evacuation dock hums around the failing beacon.",
        "player_context": "You are part of the emergency crew.",
        "situation": "The beacon is failing before the evacuation window closes.",
        "next_steps": ["Choose a lead."],
        "first_available_actions": ["Speak with Iris Vale.", "Inspect the diagnostic console."],
        "first_action_suggestions": [
            {"text": "Speak with Iris Vale.", "target_kind": "participant", "target_id": "engineer"},
            {"text": "Inspect the diagnostic console.", "target_kind": "scene_subject", "target_id": "dock_console"},
        ],
    }
    return payload


def _profiles() -> CausalProfileRegistry:
    return CausalProfileRegistry.from_directory(Path("data/genre_profiles"))


def test_phase_one_contract_validates_topology_causality_knowledge_and_freytag() -> None:
    story = validate_causal_compiled_story(_story())
    profiles = _profiles()

    assert profiles.validate(story) is story
    assert CausalCompletenessCritic().critique(story).accepted
    assert RouteFairnessCritic(profiles).critique(story).accepted
    assert FreytagProgressionCritic(profiles).critique(story).accepted


def test_freytag_critic_uses_declared_beat_order_for_revelation_gates() -> None:
    payload = _story()
    payload["required_beats"][-1]["pressure"] = 0
    story = validate_causal_compiled_story(payload)
    critic = FreytagProgressionCritic(_profiles())

    assert critic.critique(story).accepted

    payload["revelations"][0]["gate_beat_ids"] = ["resolution"]
    story = validate_causal_compiled_story(payload)

    assert "beat 'rise' opens before a revelation gate" in critic.critique(story).diagnostics


def test_mystery_profile_requires_plausible_alternative_suspect_hypotheses() -> None:
    payload = _story()
    profile = _profiles().resolve("mystery")
    payload["genre"] = "mystery"
    payload["profile"] = "mystery"
    roles = [item.role for item in (*profile.terminal_roles, *profile.causal_roles)]
    for truth in payload["truths"]:
        truth["roles"] = roles
    for index, opportunity in enumerate(payload["evidence_opportunities"]):
        opportunity["kind"] = profile.allowed_opportunity_types[index % len(profile.allowed_opportunity_types)]

    with pytest.raises(CausalValidationError, match="ALTERNATIVE_SUSPECTS_REQUIRED"):
        _profiles().validate(validate_causal_compiled_story(payload))

    payload["participants"].extend([{"id": "suspect_one", "role": "guest"}, {"id": "suspect_two", "role": "staff"}])
    payload["suspect_hypotheses"] = [
        {
            "participant_id": "suspect_one",
            "supporting_truth_ids": ["failure", "constraint"],
            "exonerating_truth_ids": ["remedy"],
        },
        {
            "participant_id": "suspect_two",
            "supporting_truth_ids": ["constraint", "remedy"],
            "exonerating_truth_ids": ["tradeoff"],
        },
    ]

    assert _profiles().validate(validate_causal_compiled_story(payload)).genre == "mystery"


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
    if genre == "mystery":
        payload["participants"].extend([{"id": "suspect_one", "role": "guest"}, {"id": "suspect_two", "role": "staff"}])
        payload["suspect_hypotheses"] = [
            {
                "participant_id": "suspect_one",
                "supporting_truth_ids": ["failure", "constraint"],
                "exonerating_truth_ids": ["remedy"],
            },
            {
                "participant_id": "suspect_two",
                "supporting_truth_ids": ["constraint", "remedy"],
                "exonerating_truth_ids": ["tradeoff"],
            },
        ]

    assert profiles.validate(validate_causal_compiled_story(payload)).genre == genre


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda value: value["causal_events"][1].update(prerequisite_event_ids=["repair_event"]), "CAUSAL_CYCLE"),
        (lambda value: value["causal_events"][1].update(earliest=1, latest=1), "TIMELINE_INVALID"),
        (lambda value: value["evidence_opportunities"][0].update(location_id="missing"), "UNKNOWN_REFERENCE"),
        (lambda value: value["evidence_opportunities"][1].update(location_id="isolated"), "UNKNOWN_REFERENCE"),
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


def test_every_end_state_must_cover_every_declared_required_outcome() -> None:
    payload = _story()
    payload["required_outcomes"].append({"id": "stabilize", "truth_id": "remedy"})

    with pytest.raises(CausalValidationError, match="ENDING_NOT_VIABLE"):
        validate_causal_compiled_story(payload)


def test_phase_one_contract_batches_every_infeasible_timeline_constraint() -> None:
    payload = _story()
    payload["causal_events"][0]["latest"] = 4
    payload["timeline_constraints"].append({"before_event_id": "repair_event", "after_event_id": "failure_event"})

    with pytest.raises(CausalValidationError, match="TIMELINE_INVALID") as raised:
        validate_causal_compiled_story(payload)

    assert "failure_event->repair_event" in raised.value.detail
    assert "repair_event->failure_event" in raised.value.detail


def test_phase_one_contract_batches_incomplete_alternative_satisfier_beats() -> None:
    payload = _story()
    payload["optional_beats"] = [
        {"id": "first_alternative", "phase": "rising_action", "pressure": 40, "purpose": "alternative_satisfier"},
        {"id": "second_alternative", "phase": "rising_action", "pressure": 45, "purpose": "alternative_satisfier"},
    ]

    with pytest.raises(CausalValidationError, match="OPTIONAL_BEAT_INCOMPLETE") as raised:
        validate_causal_compiled_story(payload)

    assert "'first_alternative'" in raised.value.detail
    assert "'second_alternative'" in raised.value.detail


def test_phase_one_contract_explains_foreign_party_knowledge_ids() -> None:
    payload = _story()
    payload["party_knowledge"][0]["truth_ids"] = ["scan"]

    with pytest.raises(CausalValidationError, match="UNKNOWN_REFERENCE") as raised:
        validate_causal_compiled_story(payload)

    assert "is evidence opportunity ID" in raised.value.detail
    assert "use truth_id 'failure'" in raised.value.detail


def test_phase_one_contract_batches_opportunities_with_unknown_realization_routes() -> None:
    payload = _story()
    payload["evidence_opportunities"][0]["route_id"] = "missing_scan_route"
    payload["evidence_opportunities"][1]["route_id"] = "missing_log_route"

    with pytest.raises(CausalValidationError, match="UNKNOWN_REFERENCE") as raised:
        validate_causal_compiled_story(payload)

    assert "scan.route_id->missing_scan_route" in raised.value.detail
    assert "log.route_id->missing_log_route" in raised.value.detail


def test_phase_one_contract_names_invalid_opportunity_reference_fields() -> None:
    payload = _story()
    payload["evidence_opportunities"][0]["holder_id"] = "dock"

    with pytest.raises(CausalValidationError, match="UNKNOWN_REFERENCE") as raised:
        validate_causal_compiled_story(payload)

    assert "scan.holder_id->dock" in raised.value.detail


def test_phase_one_contract_rejects_an_unreachable_required_opportunity() -> None:
    payload = _story()
    payload["locations"].append({"id": "sealed", "role": "sealed"})
    payload["evidence_opportunities"][0]["location_id"] = "sealed"

    with pytest.raises(CausalValidationError, match="LOCATION_UNREACHABLE"):
        validate_causal_compiled_story(payload)


def test_phase_one_contract_allows_participants_to_know_player_protected_truths() -> None:
    payload = _story()
    payload["party_knowledge"][0]["truth_ids"] = ["tradeoff"]

    assert validate_causal_compiled_story(payload).party_knowledge[0].truth_ids == ("tradeoff",)


def test_critics_reject_single_route_proof_and_missing_terminal_chain() -> None:
    payload = _story()
    payload["realization_routes"] = [item for item in payload["realization_routes"] if item["id"] != "diagnose_scan"]
    payload["evidence_opportunities"] = [item for item in payload["evidence_opportunities"] if item["id"] != "scan"]
    payload["realization_routes"][0]["failure_forward"].pop("alternative_route_ids")
    payload["causal_events"][1]["output_truths"] = ["remedy"]
    story = validate_causal_compiled_story(payload)

    assert not RouteFairnessCritic(_profiles()).critique(story).accepted
    assert not CausalCompletenessCritic().critique(story).accepted


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "relationship"))
def test_spatial_contracts_bind_immutable_cross_genre_declarations(genre: str) -> None:
    payload = _spatial_story()
    payload["genre"] = genre
    story = validate_causal_compiled_story(payload)
    bound = bind_blueprint(story)

    assert SymbolRegistry.from_story(story).ids(Namespace.MOVEMENT_PLAN) == ("engineer_to_relay",)
    assert {item.id for item in bound.scene_subjects} == {"dock_console"}
    assert {item.id for item in bound.evidence_realizations} == {
        "crew_testimony_realization",
        "relay_log",
        "repair_record",
        "scan_console",
    }
    assert bound.group_encounters[0].participants[0].id == "engineer"


@pytest.mark.parametrize(
    ("mutate", "code"),
    (
        (
            lambda story: story["participants"].__setitem__(
                1, {**story["participants"][1], "public_name": "Iris Vale"}
            ),
            "DUPLICATE_PUBLIC_NAME",
        ),
        (
            lambda story: story["participants"][0].__setitem__("initial_location_id", ["dock", "relay"]),
            "CONTRACT_INVALID",
        ),
        (lambda story: story["participants"][0].__setitem__("initial_location_id", None), "SPATIAL_PLACEMENT_REQUIRED"),
        (
            lambda story: (
                story["locations"].append({"id": "sealed", "role": "sealed"}),
                story["movement_plans"][0].__setitem__("destination_location_id", "sealed"),
            ),
            "MOVEMENT_UNREACHABLE",
        ),
        (lambda story: story["participants"][1].__setitem__("initial_availability", "away"), "GROUP_MEMBER_ABSENT"),
        (
            lambda story: story["evidence_realizations"][0].__setitem__("scene_subject_id", "missing_subject"),
            "UNKNOWN_REFERENCE",
        ),
        (lambda story: story["evidence_realizations"][0].__setitem__("location_id", "relay"), "CUSTODY_INCOMPATIBLE"),
        (
            lambda story: story["participants"][0].__setitem__(
                "public_description", "The trade-off is accepted, though nobody says why."
            ),
            "PROTECTED_PUBLIC_LEAK",
        ),
        (
            lambda story: story["opening"]["first_action_suggestions"][0].update(
                {"target_kind": "evidence_realization", "target_id": "relay_log"}
            ),
            "OPENING_SUGGESTION_UNSUPPORTED",
        ),
    ),
)
def test_spatial_contract_rejects_invalid_authoring_declarations(mutate: object, code: str) -> None:
    payload = deepcopy(_spatial_story())
    mutate(payload)

    with pytest.raises(CausalValidationError, match=code):
        validate_causal_compiled_story(payload)


def test_spatial_profile_minima_require_opening_contact_and_evidence_diversity() -> None:
    story = validate_causal_compiled_story(_spatial_story())
    profiles = CausalProfileRegistry.from_directory(Path("data/genre_profiles"))

    assert profiles.validate(story) is story

    too_few_contacts = _spatial_story()
    too_few_contacts["group_encounters"] = []
    too_few_contacts["participants"][0]["initial_availability"] = "away"
    too_few_contacts["participants"][1]["initial_availability"] = "away"
    too_few_contacts["opening"]["first_available_actions"] = []
    too_few_contacts["opening"]["first_action_suggestions"] = []
    with pytest.raises(CausalValidationError, match="INITIAL_SOCIAL_CONTACTS_REQUIRED"):
        profiles.validate(validate_causal_compiled_story(too_few_contacts))

    too_little_evidence_variety = _spatial_story()
    for realization in too_little_evidence_variety["evidence_realizations"]:
        realization["kind"] = "document"
    with pytest.raises(CausalValidationError, match="EVIDENCE_ROUTE_DIVERSITY_REQUIRED"):
        profiles.validate(validate_causal_compiled_story(too_little_evidence_variety))
