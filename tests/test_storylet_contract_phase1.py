"""Phase-1 immutable storylet authoring contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from storygame.authoring.candidate_audit import _storylet_coverage
from storygame.authoring.causal_contracts import CausalValidationError, validate_causal_compiled_story
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.sources import StoryBrief, StorySourceLoader
from storygame.authoring.storylet_critics import (
    DramaticEscalationCritic,
    FailureForwardViabilityCritic,
    ParticipantContinuityCritic,
    ProtectedKnowledgeSafetyCritic,
    StoryletCoverageCritic,
)
from storygame.authoring.symbol_resolution import Namespace, SymbolRegistry
from tests.test_causal_story_contract import _story


def _storylet_story() -> dict[str, object]:
    story = _story()
    story["dramatic_spine"] = {
        "active_conflict": "The crew must choose a costly repair before evacuation.",
        "central_question": "What cost will the crew accept to keep others safe?",
        "participant_role_requirements": ["crew"],
        "target_pressure": {"minimum": 0, "maximum": 100},
        "completion_truth_ids": ["tradeoff"],
    }
    story["consequences"] = [
        {
            "id": "commit_repair",
            "assert_truth_ids": ["tradeoff"],
            "retract_truth_ids": [],
        }
    ]
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
            "realization_modes": ["negotiation", "direct_action"],
            "consequence_ids": ["commit_repair"],
            "activation_truth_id": "failure",
            "completion_truth_id": "tradeoff",
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
            "failure_forward_storylet_ids": [],
        },
    ]
    return story


def test_storylet_contract_binds_immutable_declarations_and_profile_rules() -> None:
    story = validate_causal_compiled_story(_storylet_story())
    registry = SymbolRegistry.from_story(story)

    assert registry.ids(Namespace.STORYLET) == ("crew_debates_cost", "engineer_faces_cost")
    assert registry.ids(Namespace.CONSEQUENCE) == ("commit_repair",)
    assert CausalProfileRegistry.from_directory(Path("data/genre_profiles")).validate(story) is story
    coverage = _storylet_coverage(story)
    assert coverage.by_beat == {"crisis": 2}
    assert coverage.by_purpose == {"moral_choice": 1, "relationship": 1}
    assert coverage.by_realization_mode == {"dialogue": 1, "direct_action": 1, "negotiation": 1}
    assert coverage.by_route_family == {"crew_deliberation": 1, "repair_commitment": 1}


def test_storylet_critics_accept_a_coherent_pool_and_report_missing_coverage() -> None:
    story = validate_causal_compiled_story(_storylet_story())
    critics = (
        StoryletCoverageCritic(CausalProfileRegistry.from_directory(Path("data/genre_profiles"))),
        DramaticEscalationCritic(),
        ParticipantContinuityCritic(),
        ProtectedKnowledgeSafetyCritic(),
        FailureForwardViabilityCritic(),
    )

    assert (
        StoryletCoverageCritic(CausalProfileRegistry.from_directory(Path("data/genre_profiles")))
        .critique(story)
        .diagnostics
    )
    assert all(not critic.critique(story).diagnostics for critic in critics[1:])
    assert StoryletCoverageCritic(CausalProfileRegistry.from_directory(Path("data/genre_profiles"))).critique(
        story.model_copy(update={"storylets": ()})
    ).diagnostics == ("dramatic spine has no storylets",)


def test_storylet_reference_diagnostics_cover_every_new_namespace() -> None:
    candidate = _storylet_story()
    candidate["storylets"][0].update(
        beat_id="missing_beat",
        consequence_ids=["missing_consequence"],
        failure_forward_storylet_ids=["missing_storylet"],
    )
    candidate["storylets"][0]["availability"].update(
        participant_ids=["relay"], location_ids=["failure"], required_truth_ids=["engineer"]
    )

    with pytest.raises(CausalValidationError) as raised:
        validate_causal_compiled_story(candidate)

    assert "expected required_beat" in raised.value.detail
    assert "expected consequence" in raised.value.detail
    assert "expected storylet" in raised.value.detail
    assert "expected participant" in raised.value.detail
    assert "expected location" in raised.value.detail
    assert "expected truth" in raised.value.detail


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda value: value["storylets"][0]["availability"].update(required_truth_ids=["tradeoff"]),
            "STORYLET_PROTECTED",
        ),
        (
            lambda value: value["storylets"][0].update(failure_forward_storylet_ids=["engineer_faces_cost"]),
            "STORYLET_FAILURE_CYCLE",
        ),
        (lambda value: value["storylets"][0].update(completion_truth_id="failure"), "STORYLET_MARKER_INVALID"),
        (lambda value: value["consequences"][0].update(assert_truth_ids=["missing"]), "UNKNOWN_REFERENCE"),
    ],
)
def test_storylet_semantics_fail_locally(mutate: object, code: str) -> None:
    candidate = _storylet_story()
    mutate(candidate)  # type: ignore[operator]

    with pytest.raises(CausalValidationError, match=code):
        validate_causal_compiled_story(candidate)


def test_story_brief_normalizes_explicit_creative_direction_and_keeps_unknown_fields_closed(tmp_path: Path) -> None:
    payload = {
        "schema_version": "freytag-story-brief-v1",
        "id": "test_brief",
        "genre": "sci-fi",
        "profile": "sci-fi",
        "premise": "A hard choice awaits.",
        "opening_public_boundary": "The beacon is failing.",
        "character_arcs": ["An engineer learns to delegate."],
        "conflict_direction": ["A rescue window is closing."],
        "dramatic_spine_direction": ["The cost becomes visible."],
        "world_direction": ["A relay hangs over a gas giant."],
        "possibility_direction": ["Negotiate, repair, or investigate."],
        "presentation_direction": ["Tense, tactile, and spare."],
    }
    brief = StoryBrief.model_validate(payload)
    path = tmp_path / "brief.yaml"
    path.write_text(__import__("yaml").safe_dump(payload), encoding="utf-8")

    source = StorySourceLoader(Path("data/story_outlines.yaml"), Path("data/genre_profiles")).load_brief(path)

    assert brief.character_arcs
    assert source.creative_direction["character_arcs"] == ("An engineer learns to delegate.",)
    with pytest.raises(ValidationError):
        StoryBrief.model_validate({**payload, "unknown_direction": []})
