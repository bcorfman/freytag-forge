from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from storygame.evaluation import evaluate_fixture_playability, load_evaluation_fixtures
from storygame.story_packages import (
    StoryPackageValidationError,
    author_story_package,
    evaluate_package_playability,
    validate_story_package,
)


def _package() -> dict[str, Any]:
    return {
        "schema_version": "story-package-v1",
        "id": "clockwork-harbor",
        "genre": "fantasy",
        "tone": "hopeful",
        "locations": ["harbor", "archive"],
        "characters": [
            {
                "id": "navigator",
                "location": "harbor",
                "motivation": "Keep the fleet safe.",
                "role_contract": "navigator",
                "available": True,
            }
        ],
        "world_rules": [{"id": "tides", "cause": "moon rises", "effect": "gate opens"}],
        "secrets": [{"id": "gate-key", "known_by": ["navigator"]}],
        "clues": [
            {"id": "logbook", "reveals": ["gate-truth"]},
            {"id": "tide-chart", "reveals": ["gate-truth"]},
        ],
        "revelations": [
            {
                "id": "gate-truth",
                "requires": ["gate-key"],
                "acquisition_paths": [["logbook"], ["tide-chart"]],
                "resilient": True,
            }
        ],
        "causal_assumptions": [{"id": "open-gate", "requires": ["gate-truth"], "enables": ["sail-home"]}],
        "beat_plan": [{"id": "reveal", "requires": ["gate-truth"]}],
        "endings": [
            {
                "id": "sail-home",
                "requires_revelations": ["gate-truth"],
                "available_characters": ["navigator"],
            }
        ],
    }


def _report(critic_id: str, score: int = 95) -> dict[str, object]:
    return {
        "critic_id": critic_id,
        "scores": {"continuity": score, "causality": score, "dialogue_fit": score},
        "feedback": "The package is internally consistent.",
    }


def test_story_package_validation_checks_resilient_revelation_and_ending_reachability():
    package = validate_story_package(_package())

    assert package["id"] == "clockwork-harbor"

    invalid = _package()
    invalid["revelations"][0]["acquisition_paths"] = [["missing-clue"]]  # type: ignore[index]
    with pytest.raises(StoryPackageValidationError, match="references missing"):
        validate_story_package(invalid)


def test_story_package_validation_rejects_unavailable_ending_character():
    invalid = _package()
    invalid["endings"][0]["available_characters"] = ["missing-npc"]  # type: ignore[index]

    with pytest.raises(StoryPackageValidationError, match="references missing"):
        validate_story_package(invalid)


def test_offline_authoring_runs_parallel_specialists_then_versioned_judge():
    class Generator:
        def generate(self, request: dict[str, object]) -> dict[str, Any]:
            assert request["genre"] == "fantasy"
            return _package()

    class Critic:
        def __init__(self, critic_id: str) -> None:
            self.critic_id = critic_id

        def critique(self, package: dict[str, Any]) -> dict[str, object]:
            assert package["id"] == "clockwork-harbor"
            return _report(self.critic_id)

    result = author_story_package(
        {"genre": "fantasy"},
        Generator(),
        (Critic("continuity"), Critic("causality"), Critic("dialogue-fit")),
    )

    assert result["accepted"] is True
    assert result["judge"]["status"] == "accepted"
    assert result["evaluation"]["rubric_version"] == "story-package-rubric-v1"
    assert result["evaluation"]["direct_validity"] is True
    assert result["evaluation"]["token_usage"] > 0


def test_authoring_recovery_records_fact_categories_and_playability_covers_all_styles():
    class Generator:
        def generate(self, request: dict[str, object]) -> dict[str, Any]:
            return _package()

    class Critic:
        def __init__(self, critic_id: str) -> None:
            self.critic_id = critic_id

        def critique(self, package: dict[str, Any]) -> dict[str, object]:
            return _report(self.critic_id, score=30)

    class Recoverer:
        def recover(self, package: dict[str, Any], issues: tuple[str, ...]) -> dict[str, object]:
            assert issues
            return {
                "package": package,
                "preserved_fact_categories": ["locations", "characters", "secrets"],
                "modified_fact_categories": ["causal_assumptions"],
                "discarded_fact_categories": [],
            }

    result = author_story_package(
        {"genre": "fantasy"},
        Generator(),
        (Critic("continuity"), Critic("causality"), Critic("dialogue-fit")),
        recoverer=Recoverer(),
        max_rounds=2,
    )

    assert result["accepted"] is False
    assert result["recovery"]["attempted"] is True
    assert result["recovery"]["preserved_fact_categories"] == ("characters", "locations", "secrets")

    class Player:
        def play(self, package: dict[str, Any], style: str) -> dict[str, object]:
            return {"style": style, "ending_id": "sail-home", "artifact": {"action_outcome": "accepted"}}

    playability = evaluate_package_playability(_package(), Player())

    assert playability["passed"] is True
    assert {run["style"] for run in playability["runs"]} == {
        "exploratory",
        "goal_focused",
        "social",
        "adversarial",
        "avoidant",
        "chaotic",
    }


def test_fixture_playability_runs_all_styles_for_every_frozen_fixture():
    class PackageFactory:
        def build(self, fixture: Mapping[str, object]) -> dict[str, Any]:
            package = _package()
            package["id"] = str(fixture["id"])
            package["genre"] = str(fixture["genre"])
            package["tone"] = str(fixture["tone"])
            return package

    class Player:
        def play(self, package: dict[str, Any], style: str) -> dict[str, object]:
            return {"style": style, "ending_id": "sail-home", "artifact": {"action_outcome": "accepted"}}

    results = evaluate_fixture_playability(PackageFactory(), Player())

    assert set(results) == {fixture["id"] for fixture in load_evaluation_fixtures()}
