"""Phase-2 profile and semantic validation contracts for Story Blueprints."""

from __future__ import annotations

from copy import deepcopy

import pytest

from storygame.authoring.blueprint_contracts import BlueprintValidationError, load_story_blueprint_fixture
from storygame.authoring.genre_profiles import GenreProfileRegistry


@pytest.fixture(scope="module")
def registry() -> GenreProfileRegistry:
    return GenreProfileRegistry.from_directory()


@pytest.mark.parametrize("genre", ["mystery", "fantasy", "sci-fi", "relationship"])
def test_checked_in_fixture_satisfies_its_declared_genre_profile(registry: GenreProfileRegistry, genre: str) -> None:
    blueprint = load_story_blueprint_fixture(genre)

    validator = registry.resolve(blueprint.genre)

    assert validator.validate(blueprint) is blueprint


def test_registry_rejects_a_genre_without_an_injected_profile(registry: GenreProfileRegistry) -> None:
    blueprint = load_story_blueprint_fixture("fantasy").model_copy(update={"genre": "western"})

    with pytest.raises(BlueprintValidationError, match="GENRE_PROFILE_NOT_FOUND"):
        registry.validate(blueprint)


def test_mystery_requires_one_complete_crime_solution(registry: GenreProfileRegistry) -> None:
    payload = load_story_blueprint_fixture("mystery").model_dump(mode="json")
    payload["genre_causality"] = [binding for binding in payload["genre_causality"] if binding["role"] != "concealment"]

    with pytest.raises(BlueprintValidationError, match="GENRE_CAUSAL_ROLE_REQUIRED"):
        registry.validate(load_story_blueprint_fixture("mystery").__class__.model_validate(payload))


def test_mystery_rejects_a_climax_without_required_discoveries(registry: GenreProfileRegistry) -> None:
    payload = load_story_blueprint_fixture("mystery").model_dump(mode="json")
    climax = next(beat for beat in payload["required_beats"] if beat["role"] == "climax")
    climax["revelation_dependencies"] = []

    with pytest.raises(BlueprintValidationError, match="CLIMAX_UNSUPPORTED"):
        registry.validate(load_story_blueprint_fixture("mystery").__class__.model_validate(payload))


def test_mystery_requires_evidence_backed_identification(registry: GenreProfileRegistry) -> None:
    blueprint = load_story_blueprint_fixture("mystery")
    payload = blueprint.model_dump(mode="json")
    payload["realization_routes"][0]["role"] = "testimony"

    with pytest.raises(BlueprintValidationError, match="EVIDENCE_ROUTE_REQUIRED"):
        registry.validate(blueprint.__class__.model_validate(payload))


def test_mystery_rejects_circular_clue_placement(registry: GenreProfileRegistry) -> None:
    blueprint = load_story_blueprint_fixture("mystery")
    payload = blueprint.model_dump(mode="json")
    payload["realization_routes"][0]["availability_constraints"] = ["identity_proof"]

    with pytest.raises(BlueprintValidationError, match="CIRCULAR_PROOF"):
        registry.validate(blueprint.__class__.model_validate(payload))


@pytest.mark.parametrize(
    ("genre", "role"),
    [
        ("fantasy", "cost"),
        ("sci-fi", "trade_off"),
        ("relationship", "choice"),
    ],
)
def test_non_mystery_profiles_require_their_own_causality(
    registry: GenreProfileRegistry, genre: str, role: str
) -> None:
    blueprint = load_story_blueprint_fixture(genre)
    payload = blueprint.model_dump(mode="json")
    payload["genre_causality"] = [binding for binding in payload["genre_causality"] if binding["role"] != role]

    with pytest.raises(BlueprintValidationError, match="GENRE_CAUSAL_ROLE_REQUIRED"):
        registry.validate(blueprint.__class__.model_validate(payload))


@pytest.mark.parametrize("genre", ["mystery", "fantasy", "sci-fi", "relationship"])
def test_profiles_reject_an_unsupported_revelation_role(registry: GenreProfileRegistry, genre: str) -> None:
    blueprint = load_story_blueprint_fixture(genre)
    payload = blueprint.model_dump(mode="json")
    payload["revelations"][0]["role"] = "unsupported"

    with pytest.raises(BlueprintValidationError, match="REVELATION_ROLE_INVALID"):
        registry.validate(blueprint.__class__.model_validate(payload))


def test_profile_rejects_out_of_order_turning_points(registry: GenreProfileRegistry) -> None:
    blueprint = load_story_blueprint_fixture("sci-fi")
    payload = deepcopy(blueprint.model_dump(mode="json"))
    crisis = next(beat for beat in payload["required_beats"] if beat["role"] == "crisis")
    crisis["phase"] = "exposition"

    with pytest.raises(BlueprintValidationError, match="PHASE_ORDER_INVALID"):
        registry.validate(blueprint.__class__.model_validate(payload))
