from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from storygame.authoring.bound_ir import bind_blueprint
from storygame.authoring.causal_contracts import CausalValidationError, validate_causal_compiled_story
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.symbol_resolution import Namespace, SymbolRegistry
from tests.test_causal_story_contract import _spatial_story


def _interaction_story() -> dict[str, object]:
    story = _spatial_story()
    story["truths"].extend(
        (
            {"id": "interaction_continuing", "summary": "The conversation remains active."},
            {"id": "interaction_aborted", "summary": "The conversation ended without agreement."},
            {"id": "interaction_recent", "summary": "The conversation was recently used."},
        )
    )
    story["participants"][0]["performance_profile_id"] = "engineer_manner"
    story["npc_performance_profiles"] = [
        {
            "id": "engineer_manner",
            "participant_id": "engineer",
            "public_manner": "Focused, candid, and protective of the crew.",
            "voice": {
                "register": "familiar and direct",
                "cadence": "brief observations followed by a concrete proposal",
                "diction": "practical and specific",
                "avoidances": ["bureaucratic phrasing", "repeated catchphrases"],
            },
            "behavioral_cues": ["checks the warning display before discussing risk"],
        }
    ]
    story["dramatic_spine"] = {
        "active_conflict": "The crew must choose a costly repair before evacuation.",
        "central_question": "What cost will the crew accept to keep others safe?",
        "participant_role_requirements": ["crew"],
        "target_pressure": {"minimum": 0, "maximum": 100},
        "completion_truth_ids": ["tradeoff"],
    }
    story["consequences"] = [{"id": "commit_repair", "assert_truth_ids": ["tradeoff"], "retract_truth_ids": []}]
    story["storylets"] = [
        {
            "id": "engineer_faces_cost",
            "beat_id": "crisis",
            "purpose": "moral_choice",
            "route_family": "repair_commitment",
            "availability": {
                "required_truth_ids": ["failure"],
                "participant_ids": ["engineer"],
                "location_ids": ["relay"],
                "pressure": {"minimum": 1, "maximum": 70},
            },
            "priority": 70,
            "dramatic_question": "What will the engineer sacrifice?",
            "realization_modes": ["negotiation"],
            "consequence_ids": ["commit_repair"],
            "activation_truth_id": "failure",
            "completion_truth_id": "tradeoff",
            "abort_truth_ids": ["interaction_aborted"],
            "failure_forward_storylet_ids": ["crew_debates_cost"],
        },
        {
            "id": "crew_debates_cost",
            "beat_id": "crisis",
            "purpose": "relationship",
            "route_family": "crew_deliberation",
            "availability": {
                "required_truth_ids": ["failure"],
                "participant_ids": ["engineer"],
                "location_ids": ["relay"],
                "pressure": {"minimum": 1, "maximum": 70},
            },
            "priority": 60,
            "dramatic_question": "Who will bear the cost?",
            "realization_modes": ["dialogue"],
            "consequence_ids": ["commit_repair"],
            "activation_truth_id": "failure",
            "completion_truth_id": "tradeoff",
            "abort_truth_ids": ["interaction_aborted"],
            "failure_forward_storylet_ids": [],
            "interaction_frame_ids": ["engineer_warning"],
        },
    ]
    story["interaction_frames"] = [
        {
            "id": "engineer_warning",
            "storylet_id": "crew_debates_cost",
            "initiator_id": "engineer",
            "participant_ids": ["engineer"],
            "initiation": "npc_initiated",
            "location_ids": ["relay"],
            "dramatic_objective": "Win consent for the risky repair.",
            "opening_move": "Name the immediate danger and invite a decision.",
            "response_obligations": ["answer direct concerns about crew safety"],
            "allowed_tactics": ["warn", "reassure"],
            "agency_modes": ["engage", "refuse", "redirect"],
            "permitted_movement_plan_ids": ["engineer_to_relay"],
            "activation_truth_id": "failure",
            "continuation_truth_id": "interaction_continuing",
            "completion_truth_id": "tradeoff",
            "abort_truth_ids": ["interaction_aborted"],
            "recent_use_truth_id": "interaction_recent",
            "failure_forward_frame_ids": [],
        }
    ]
    return story


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "relationship"))
def test_interaction_contracts_bind_immutable_cross_genre_declarations(genre: str) -> None:
    payload = _interaction_story()
    payload["genre"] = genre

    story = validate_causal_compiled_story(payload)
    bound = bind_blueprint(story)

    assert SymbolRegistry.from_story(story).ids(Namespace.NPC_PERFORMANCE_PROFILE) == ("engineer_manner",)
    assert SymbolRegistry.from_story(story).ids(Namespace.INTERACTION_FRAME) == ("engineer_warning",)
    assert bound.interaction_frames[0].storylet.id == "crew_debates_cost"
    assert bound.interaction_frames[0].initiator.id == "engineer"
    assert bound.interaction_frames[0].permitted_movement_plans[0].id == "engineer_to_relay"
    assert story.model_dump()["npc_performance_profiles"][0]["voice"]["register"] == "familiar and direct"


@pytest.mark.parametrize(
    ("mutate", "code"),
    (
        (lambda story: story["participants"][0].pop("performance_profile_id"), "NPC_PROFILE_REQUIRED"),
        (lambda story: story["interaction_frames"][0].update(initiator_id="missing_npc"), "UNKNOWN_REFERENCE"),
        (
            lambda story: story["interaction_frames"][0].update(location_ids=["dock"]),
            "INTERACTION_LOCATION_INCOMPATIBLE",
        ),
        (
            lambda story: story["storylets"][1].update(realization_modes=["negotiation"]),
            "INTERACTION_DIALOGUE_REQUIRED",
        ),
        (
            lambda story: story["movement_plans"][0].update(participant_id="navigator"),
            "INTERACTION_MOVEMENT_UNREACHABLE",
        ),
        (
            lambda story: story["npc_performance_profiles"][0].update(public_manner="The trade-off is accepted."),
            "PROTECTED_PUBLIC_LEAK",
        ),
        (
            lambda story: story["interaction_frames"][0].update(continuation_truth_id="tradeoff"),
            "INTERACTION_MARKER_INVALID",
        ),
        (lambda story: story["interaction_frames"][0].update(agency_modes=[]), "INTERACTION_AGENCY_REQUIRED"),
    ),
)
def test_interaction_contract_rejects_invalid_declarations(mutate: object, code: str) -> None:
    payload = deepcopy(_interaction_story())
    mutate(payload)

    with pytest.raises(CausalValidationError, match=code):
        validate_causal_compiled_story(payload)


def test_interaction_failure_forward_frames_must_be_acyclic() -> None:
    payload = deepcopy(_interaction_story())
    alternate = deepcopy(payload["interaction_frames"][0])
    alternate.update(id="engineer_warning_alternate", failure_forward_frame_ids=["engineer_warning"])
    payload["interaction_frames"][0]["failure_forward_frame_ids"] = ["engineer_warning_alternate"]
    payload["interaction_frames"].append(alternate)
    payload["storylets"][1]["interaction_frame_ids"].append("engineer_warning_alternate")

    with pytest.raises(CausalValidationError, match="INTERACTION_FAILURE_CYCLE"):
        validate_causal_compiled_story(payload)


def test_interaction_reference_diagnostics_cover_each_phase_two_namespace() -> None:
    payload = deepcopy(_interaction_story())
    payload["participants"][0]["performance_profile_id"] = "missing_profile"
    payload["npc_performance_profiles"][0]["participant_id"] = "relay"
    payload["storylets"][1]["interaction_frame_ids"] = ["missing_frame"]
    payload["interaction_frames"][0].update(
        storylet_id="missing_storylet",
        participant_ids=["missing_participant"],
        location_ids=["missing_location"],
        permitted_movement_plan_ids=["missing_movement"],
        completion_truth_id="missing_completion",
        abort_truth_ids=["missing_abort"],
        failure_forward_frame_ids=["missing_forward_frame"],
    )

    with pytest.raises(CausalValidationError) as raised:
        validate_causal_compiled_story(payload)

    for namespace in (
        "npc_performance_profile",
        "participant",
        "interaction_frame",
        "storylet",
        "location",
        "movement_plan",
        "truth",
    ):
        assert f"expected {namespace}" in raised.value.detail


def test_npc_initiation_requires_present_or_declared_movable_initiator() -> None:
    payload = deepcopy(_interaction_story())
    payload["interaction_frames"][0]["permitted_movement_plan_ids"] = []

    with pytest.raises(CausalValidationError, match="INTERACTION_INITIATOR_UNAVAILABLE"):
        validate_causal_compiled_story(payload)


def test_interaction_profile_minima_preserve_route_diversity_and_player_agency() -> None:
    story = validate_causal_compiled_story(_interaction_story())
    profiles = CausalProfileRegistry.from_directory(Path("data/genre_profiles"))
    profiles.validate(story)

    sparse = deepcopy(_interaction_story())
    sparse["interaction_frames"][0]["allowed_tactics"] = ["warn"]
    sparse_story = validate_causal_compiled_story(sparse)
    with pytest.raises(CausalValidationError, match="CONVERSATIONAL_ROUTE_DIVERSITY_REQUIRED"):
        profiles.validate(sparse_story)
