"""Phase-1 contracts for immutable, genre-agnostic story blueprints."""

from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from storygame.authoring.blueprint_contracts import (
    BlueprintValidationError,
    load_story_blueprint_fixture,
    validate_story_blueprint,
)
from storygame.authoring.blueprint_migration import compiled_story_as_blueprint
from storygame.authoring.compiler import load_compiled_story_fixture


def _blueprint(genre: str = "mystery") -> dict[str, object]:
    return {
        "schema_version": "story-blueprint-v1",
        "id": f"{genre.replace('-', '_')}_sample",
        "version": 1,
        "source_outline": {"id": f"{genre.replace('-', '_')}_outline", "content_hash": "a" * 64},
        "genre": genre,
        "title": "A Test Story",
        "premise": "A protagonist must act before a threatened ending becomes permanent.",
        "central_question": "Can the protagonist reach a viable ending?",
        "canonical_truths": [
            {"id": "opening_known", "summary": "The opening situation is established."},
            {"id": "key_evidence", "summary": "A decisive truth can be established."},
            {"id": "ending_ready", "summary": "The ending conditions are true."},
        ],
        "protected_facts": [{"id": "protected_answer", "truth_id": "ending_ready", "release_after": ["discover_key"]}],
        "revelations": [
            {
                "id": "discover_key",
                "summary": "The player can establish the decisive truth.",
                "prerequisite_truths": ["opening_known"],
                "completion_conditions": ["key_evidence"],
                "protected_facts": ["protected_answer"],
                "unlocks": ["resolve_story"],
                "required": True,
            },
            {
                "id": "resolve_story",
                "summary": "The player can make the final choice.",
                "prerequisite_revelations": ["discover_key"],
                "completion_conditions": ["ending_ready"],
                "required": True,
            },
        ],
        "realization_routes": [
            {
                "id": "find_document",
                "revelation_id": "discover_key",
                "role": "document",
                "satisfiers": [{"truth_id": "key_evidence", "operator": "establish"}],
                "availability_constraints": ["opening_known"],
                "failure_forward": {"result_truths": ["key_evidence"]},
            },
            {
                "id": "make_choice",
                "revelation_id": "resolve_story",
                "role": "choice",
                "satisfiers": [{"truth_id": "ending_ready", "operator": "establish"}],
                "availability_constraints": ["key_evidence"],
                "failure_forward": {"result_truths": ["ending_ready"]},
            },
        ],
        "required_beats": [
            {
                "id": "establish_answer",
                "phase": "rising_action",
                "role": "discovery",
                "question": "What changes the situation?",
                "required_outcome": "key_evidence",
                "revelation_dependencies": ["discover_key"],
                "pressure_change": 1,
                "pacing": 2,
            },
            {
                "id": "final_choice",
                "phase": "resolution",
                "role": "resolution",
                "question": "Can the protagonist reach a viable ending?",
                "required_outcome": "ending_ready",
                "revelation_dependencies": ["resolve_story"],
                "pressure_change": -1,
                "pacing": 3,
            },
        ],
        "optional_beats": [
            {
                "id": "complication",
                "phase": "midpoint_reversal",
                "role": "complication",
                "narrative_function": "Increase pressure without becoming required.",
                "optional_purpose": "complication",
                "pressure_change": 1,
                "pacing": 2,
            }
        ],
        "opposition_clocks": [{"id": "threat", "summary": "Pressure rises.", "opportunity_decay": 1, "max_ticks": 4}],
        "end_states": [
            {
                "id": "survival",
                "summary": "The story reaches a viable conclusion.",
                "required_truths": ["ending_ready"],
                "required_revelations": ["discover_key", "resolve_story"],
                "answers_central_question": True,
            }
        ],
    }


def _disconnect_route(value: dict[str, object]) -> None:
    route = value["realization_routes"][0]
    route["satisfiers"] = [{"truth_id": "opening_known", "operator": "establish"}]
    route["failure_forward"] = {"result_truths": ["opening_known"]}


@pytest.mark.parametrize("genre", ["mystery", "fantasy", "sci-fi", "relationship"])
def test_contract_validates_a_minimal_cross_genre_blueprint(genre: str) -> None:
    blueprint = validate_story_blueprint(_blueprint(genre))

    assert blueprint.genre == genre
    assert blueprint.realization_routes[0].failure_forward.result_truths == ("key_evidence",)


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda value: value["canonical_truths"].append({"id": "key_evidence", "summary": "Duplicate."}),
            "DUPLICATE_ID",
        ),
        (lambda value: value["revelations"][0].update(unlocks=["missing"]), "UNKNOWN_REFERENCE"),
        (lambda value: value["revelations"][0].update(prerequisite_revelations=["resolve_story"]), "REVELATION_CYCLE"),
        (lambda value: value["protected_facts"][0].update(release_after=["missing"]), "UNKNOWN_REFERENCE"),
        (
            lambda value: value["realization_routes"][0].update(availability_constraints=["missing"]),
            "UNKNOWN_REFERENCE",
        ),
        (_disconnect_route, "ROUTE_DOES_NOT_SATISFY_REVELATION"),
        (lambda value: value["end_states"][0].update(required_revelations=["discover_key"]), "ENDING_NOT_VIABLE"),
    ],
)
def test_contract_rejects_malformed_graphs(mutate, code: str) -> None:
    payload = _blueprint()
    mutate(payload)

    with pytest.raises(BlueprintValidationError, match=code):
        validate_story_blueprint(payload)


def test_contract_rejects_optional_beat_that_becomes_only_required_outcome_route() -> None:
    payload = _blueprint()
    payload["required_beats"] = payload["required_beats"][1:]
    payload["optional_beats"] = [
        {
            "id": "only_route",
            "phase": "rising_action",
            "role": "discovery",
            "optional_purpose": "alternative_satisfier",
            "required_outcome": "key_evidence",
            "revelation_dependencies": ["discover_key"],
            "pressure_change": 1,
            "pacing": 2,
        }
    ]

    with pytest.raises(BlueprintValidationError, match="OPTIONAL_ONLY_REQUIRED_OUTCOME"):
        validate_story_blueprint(payload)


def test_contract_is_immutable_after_parsing() -> None:
    blueprint = validate_story_blueprint(deepcopy(_blueprint()))

    with pytest.raises(ValidationError):
        blueprint.title = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize("genre", ["mystery", "fantasy", "sci-fi", "relationship"])
def test_checked_in_cross_genre_blueprint_fixtures_load(genre: str) -> None:
    assert load_story_blueprint_fixture(genre).genre == genre


@pytest.mark.parametrize("genre", ["mystery", "fantasy", "sci-fi", "relationship"])
def test_compiled_story_remains_a_public_api_and_can_project_to_a_reduced_blueprint(genre: str) -> None:
    blueprint = compiled_story_as_blueprint(load_compiled_story_fixture(genre))

    assert blueprint.genre == genre
