"""Phase-0 authoring-quality baselines; these do not exercise runtime mutation."""

from __future__ import annotations

import pytest

from storygame.authoring.compiler import load_compiled_story_fixture

SUPPORTED_GENRES = ("mystery", "fantasy", "sci-fi", "relationship")


@pytest.mark.authoring_quality
@pytest.mark.parametrize("genre", SUPPORTED_GENRES)
def test_every_supported_genre_has_a_loadable_authoring_fixture(genre: str) -> None:
    story = load_compiled_story_fixture(genre)

    assert story.genre == genre
    assert story.id
    assert story.central_question


@pytest.mark.authoring_quality
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Phase 0 baseline: Vale's reduced CompiledStory lacks the Blueprint crime solution, "
        "proof threshold, and alternate realization routes required for the first vertical slice."
    ),
)
def test_vale_blueprint_vertical_slice_requires_complete_causality_and_fair_routes() -> None:
    """Keep the known Vale gap visible until Phase 4 supplies the reviewed blueprint."""

    story = load_compiled_story_fixture("mystery")
    blueprint = story.model_dump(mode="json")
    solution = blueprint["crime_solution"]

    assert set(solution) >= {
        "victim",
        "perpetrator",
        "motive",
        "means",
        "opportunity",
        "method",
        "timeline",
        "concealment",
        "exonerating_evidence",
        "proof_threshold",
    }
    pivotal_revelations = [revelation for revelation in blueprint["revelations"] if revelation["required"]]
    assert pivotal_revelations
    assert all(len(revelation["realization_routes"]) >= 2 for revelation in pivotal_revelations)
