from __future__ import annotations

from copy import deepcopy

import pytest

from storygame.authoring.candidate_review import required_review_checklist
from storygame.authoring.causal_contracts import CausalCompiledStory, validate_causal_compiled_story
from storygame.authoring.prompts import build_blueprint_compiler_prompt
from storygame.authoring.spatial_interaction_critics import (
    InteractionViabilityCritic,
    SpatialContinuityCritic,
)
from tests.test_causal_spatial_projection_phase2 import _interaction_story
from tests.test_causal_story_contract import _story


def _phase3_story() -> dict[str, object]:
    story = _interaction_story()
    for item in (
        ("opening_orientation", "setup", "investigation", "opening_route", "opening", "dock", 0),
        ("rising_pressure", "rise", "social_complication", "pressure_route", "failure", "relay", 1),
        ("repair_climax", "climax", "conflict", "climax_route", "failure", "relay", 3),
        ("safe_resolution", "resolution", "transition", "resolution_route", "failure", "relay", 4),
    ):
        story["storylets"].append(
            {
                "id": item[0],
                "beat_id": item[1],
                "purpose": item[2],
                "route_family": item[3],
                "availability": {
                    "required_truth_ids": [item[4]],
                    "participant_ids": ["engineer"],
                    "location_ids": [item[5]],
                    "pressure": {"minimum": item[6], "maximum": item[6]},
                },
                "priority": 50,
                "dramatic_question": f"How will the crew face {item[1]}?",
                "realization_modes": ["direct_action"],
                "consequence_ids": ["commit_repair"],
                "activation_truth_id": item[4],
                "completion_truth_id": "tradeoff",
            }
        )
    return story


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "relationship"))
def test_phase_three_critics_accept_playable_cross_genre_interactions(genre: str) -> None:
    payload = _phase3_story()
    payload["genre"] = genre
    story = validate_causal_compiled_story(payload)

    assert SpatialContinuityCritic().critique(story).accepted
    assert InteractionViabilityCritic().critique(story).accepted


def test_spatial_critic_requires_realization_and_continuous_actor_paths() -> None:
    missing_projection = validate_causal_compiled_story(_story())
    result = SpatialContinuityCritic().critique(missing_projection)
    assert not result.accepted
    assert "playable spatial realization" in result.diagnostics[0]

    payload = deepcopy(_interaction_story())
    payload["locations"].append({"id": "sealed_bay", "role": "isolated"})
    payload["causal_events"][1]["location_id"] = "sealed_bay"
    story = CausalCompiledStory.model_validate(payload)
    result = SpatialContinuityCritic().critique(story)

    assert not result.accepted
    assert "repair_event" in " ".join(result.diagnostics)
    assert "engineer" in " ".join(result.diagnostics)


def test_interaction_critic_reports_dead_ends_repetition_voice_and_knowledge() -> None:
    payload = deepcopy(_interaction_story())
    frame = payload["interaction_frames"][0]
    frame["response_obligations"] = []
    frame["allowed_tactics"] = ["warn", "warn"]
    payload["npc_performance_profiles"] = []
    payload["participants"][0]["performance_profile_id"] = None
    payload["movement_plans"][0]["participant_id"] = "navigator"
    frame["agency_modes"] = ["engage"]
    frame["opening_move"] = "Reveal that the trade-off is accepted."
    story = CausalCompiledStory.model_validate(payload)

    result = InteractionViabilityCritic().critique(story)

    assert not result.accepted
    diagnostics = " ".join(result.diagnostics)
    assert "response obligations" in diagnostics
    assert "repeats tactic" in diagnostics
    assert "performance profile" in diagnostics
    assert "participant agency" in diagnostics
    assert "unsupported material movement" in diagnostics
    assert "protected truth" in diagnostics


def test_compiler_prompt_plans_space_and_conversation_before_routes() -> None:
    prompt = build_blueprint_compiler_prompt(
        "A crew must solve a crisis.",
        {"genre": "sci-fi", "minimum_independent_proof_routes": 2},
        {"source_format": "story-outline-inventory-v1", "source_id": "signal", "source_hash": "a" * 64},
        source_profile="sci-fi",
        diagnostics=({"critic": "spatial_continuity", "code": "SPATIAL_CONTINUITY", "detail": "repair the path"},),
    )

    spatial = prompt.index("Plan the spatial timeline")
    routes = prompt.index("Then plan revelation and realization routes")
    storylets = prompt.index("Then generate the dramatic spine, storylet pool, and interaction frames")
    assert spatial < routes < storylets
    assert "public presentation must be separate from private motive, knowledge, deception, and scene goal" in prompt
    assert "npc_performance_profiles" in prompt
    assert "movement_plans, scene_subjects, evidence_realizations, group_encounters" in prompt
    assert "initiator, dramatic objective, at least two distinct tactics, response obligations" in prompt
    assert "SPATIAL_CONTINUITY repair protocol" in prompt
    assert "INTERACTION_VIABILITY repair protocol" in prompt


def test_human_review_requires_distinct_nonstereotyped_character_profiles() -> None:
    checklist = required_review_checklist()

    assert "character_voice_distinction" in checklist
    assert "catchphrase_and_stereotype_safety" in checklist
