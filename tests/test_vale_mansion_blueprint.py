"""Player-facing Phase-4 acceptance contracts for the reviewed Vale blueprint.

These tests intentionally exercise immutable authoring data. Runtime realization
and turn execution remain Phase 5 work.
"""

from __future__ import annotations

from collections.abc import Iterable

from storygame.authoring.blueprint_contracts import RealizationRoute, StoryBlueprint, load_story_blueprint_fixture
from storygame.authoring.genre_profiles import GenreProfileRegistry


def _apply(route: RealizationRoute, established: set[str]) -> set[str]:
    """Model the evidence a route can commit, including its declared fallback."""

    assert set(route.availability_constraints) <= established
    return (
        established
        | {item.truth_id for item in route.satisfiers if item.operator == "establish"}
        | set(route.failure_forward.result_truths)
    )


def _routes(story: StoryBlueprint, revelation_id: str) -> tuple[RealizationRoute, ...]:
    return tuple(route for route in story.realization_routes if route.revelation_id == revelation_id)


def _play(story: StoryBlueprint, route_ids: Iterable[str]) -> set[str]:
    routes = {route.id: route for route in story.realization_routes}
    established: set[str] = set()
    for route_id in route_ids:
        established = _apply(routes[route_id], established)
    return established


def test_reviewed_vale_blueprint_is_a_valid_mystery_profile() -> None:
    story = load_story_blueprint_fixture("vale_mansion_case")

    assert GenreProfileRegistry.from_directory().validate(story) is story
    assert story.id == "vale_mansion_case"


def test_every_pivotal_vale_revelation_has_two_distinct_fair_routes() -> None:
    story = load_story_blueprint_fixture("vale_mansion_case")

    for revelation in story.revelations:
        routes = _routes(story, revelation.id)
        assert len(routes) >= 2
        assert len({route.role for route in routes}) >= 2
        assert all(route.location_classes and route.failure_forward.result_truths for route in routes)


def test_two_player_routes_can_fairly_solve_the_vale_case() -> None:
    story = load_story_blueprint_fixture("vale_mansion_case")
    endings = story.end_states[0]

    physical_route = _play(
        story,
        [
            "inspect_gallery_staging",
            "find_ledger_leaf",
            "inspect_delivery_log",
            "recover_letter_opener_trace",
            "present_physical_case",
        ],
    )
    document_and_testimony_route = _play(
        story,
        [
            "review_case_file",
            "question_estate_clerk",
            "question_kitchen_witness",
            "reconcile_harrow_accounts",
            "confront_harrow_with_accounts",
        ],
    )

    assert set(endings.required_truths) <= physical_route
    assert set(endings.required_truths) <= document_and_testimony_route


def test_early_groundskeeper_accusation_and_unrelated_action_do_not_complete_the_case() -> None:
    story = load_story_blueprint_fixture("vale_mansion_case")
    endings = story.end_states[0]
    early_evidence = _play(story, ["review_case_file", "question_estate_clerk", "inspect_delivery_log"])
    unrelated_action = set(early_evidence)

    assert "crime_solution" not in early_evidence
    assert not set(endings.required_truths) <= early_evidence
    assert unrelated_action == early_evidence


def test_failed_or_contaminated_clue_route_moves_the_case_forward_without_releasing_protected_truth() -> None:
    story = load_story_blueprint_fixture("vale_mansion_case")
    protected = {item.truth_id: item.release_after for item in story.protected_facts}
    established = _play(story, ["inspect_gallery_staging", "find_ledger_leaf"])

    assert "payment_trail" in established
    assert "perpetrator_identity" not in established
    assert protected["perpetrator_identity"] == ("establish_harrow_case",)
    assert protected["crime_solution"] == ("decide_case_outcome",)
