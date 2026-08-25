from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from storygame.authoring.compiler import (
    CompilationError,
    CompiledStoryCompiler,
    load_compiled_story_fixture,
    validate_compiled_story,
)
from storygame.authoring.contracts import CompiledStory
from storygame.runtime.state import bootstrap_runtime_state


def _story_payload() -> dict[str, object]:
    return {
        "schema_version": "compiled-story-v1",
        "id": "harbor_signal",
        "version": 1,
        "genre": "sci-fi",
        "title": "Harbor Signal",
        "premise": "A failing beacon strands a station above an unstable sea.",
        "central_question": "Will the crew restore the beacon before the evacuation window closes?",
        "initial_world_state": {"location": "dock", "situation": "The beacon is failing."},
        "characters": [{"id": "pilot", "name": "Ira", "role": "pilot", "description": "A practical shuttle pilot."}],
        "protected_revelations": [
            {"id": "sabotage", "summary": "The outage was deliberate.", "reveal_after": ["trace_source"]}
        ],
        "beats": [
            {
                "id": "trace_signal",
                "phase": "rising_action",
                "summary": "Trace the anomalous signal.",
                "completion_tags": [{"id": "trace_source", "description": "The signal source is traced."}],
                "pacing": {"nudge_after": 2, "advance_after": 4, "escalate_after": 6, "force_consequence_after": 8},
            },
            {
                "id": "contain_crisis",
                "phase": "crisis",
                "summary": "Contain the spreading failure.",
                "prerequisites": ["trace_signal"],
                "completion_tags": [{"id": "contain_failure", "description": "The failure is contained."}],
                "pacing": {"nudge_after": 1, "advance_after": 3, "escalate_after": 5, "force_consequence_after": 7},
            },
            {
                "id": "restore_beacon",
                "phase": "climax",
                "summary": "Choose how to restore the beacon.",
                "prerequisites": ["contain_crisis"],
                "completion_tags": [{"id": "beacon_restored", "description": "The beacon is restored."}],
                "pacing": {"nudge_after": 1, "advance_after": 2, "escalate_after": 4, "force_consequence_after": 6},
            },
            {
                "id": "answer_question",
                "phase": "resolution",
                "summary": "Show whether the crew escaped the evacuation.",
                "prerequisites": ["restore_beacon"],
                "answers_central_question": True,
                "completion_tags": [{"id": "crew_safe", "description": "The crew's fate is known."}],
                "pacing": {"nudge_after": 1, "advance_after": 2, "escalate_after": 3, "force_consequence_after": 5},
            },
        ],
    }


def test_compiled_story_contract_and_local_validation_accept_valid_story():
    story = validate_compiled_story(_story_payload())

    assert isinstance(story, CompiledStory)
    assert story.id == "harbor_signal"
    assert story.beats[-1].answers_central_question is True


def test_typed_opening_contact_is_validated_and_survives_runtime_bootstrap():
    payload = _story_payload()
    payload["initial_world_state"] = {"location": "dock"}
    payload["opening"] = {
        "scene": "The storm-lashed dock.",
        "protagonist_context": "You are the station pilot sent to restore the beacon.",
        "arrival_context": "Your shuttle has just reached the dock.",
        "public_briefing": ["The beacon is failing."],
        "scene_purpose": "Establish the failing beacon and the available help.",
        "contacts": [
            {
                "id": "pilot",
                "name": "Ira",
                "role": "pilot",
                "relationship": "You are responsible for the crew together.",
                "location": "dock",
                "public_knowledge": ["The beacon is failing."],
                "item_custody": [],
            }
        ],
        "first_available_actions": ["Question Ira", "Inspect the beacon"],
    }

    story = validate_compiled_story(payload)
    state = bootstrap_runtime_state(story)

    assert state.world.attributes["opening_facts"]["contacts"][0]["id"] == "pilot"


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda value: value["characters"].append(deepcopy(value["characters"][0])), "DUPLICATE_ID"),
        (lambda value: value["beats"][1].update({"prerequisites": ["missing"]}), "UNKNOWN_REFERENCE"),
        (lambda value: value["beats"][0].update({"prerequisites": ["answer_question"]}), "PREREQUISITE_CYCLE"),
        (lambda value: value.update({"beats": value["beats"][:2]}), "MISSING_REQUIRED_PHASE"),
        (lambda value: value["beats"][2].update({"prerequisites": []}), "CLIMAX_PREREQUISITE_REQUIRED"),
        (
            lambda value: value["beats"][1].update({"required": False}),
            "CLIMAX_PREREQUISITE_REQUIRED",
        ),
        (lambda value: value["beats"][3].update({"answers_central_question": False}), "RESOLUTION_ANSWER_REQUIRED"),
        (lambda value: value["beats"][0].update({"completion_tags": []}), "COMPLETION_TAG_REQUIRED"),
        (
            lambda value: value["protected_revelations"][0].update({"reveal_after": ["missing_tag"]}),
            "UNKNOWN_REFERENCE",
        ),
        (
            lambda value: value["beats"][0].update(
                {
                    "pacing": {
                        "nudge_after": 3,
                        "advance_after": 2,
                        "escalate_after": 4,
                        "force_consequence_after": 5,
                    }
                }
            ),
            "INVALID_PACING",
        ),
    ],
)
def test_compiler_validation_rejects_each_story_agnostic_invalid_condition(mutate, code):
    payload = _story_payload()
    mutate(payload)

    with pytest.raises(CompilationError, match=code):
        validate_compiled_story(payload)


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "relationship"))
def test_checked_in_cross_genre_fixtures_are_versioned_and_valid(genre: str):
    story = load_compiled_story_fixture(genre)

    assert story.schema_version == "compiled-story-v1"
    assert story.genre == genre


def test_mystery_runtime_fixture_loads_the_approved_causal_artifact():
    story = load_compiled_story_fixture("mystery")

    assert story.id == "vale_mansion_rebuild"
    assert story.title == "Death in the West Gallery"
    location = story.initial_world_state["location"]
    navigation = story.initial_world_state["navigation"]
    assert location in navigation["names"]
    assert any(route["from"] == location for route in navigation["routes"])
    assert story.beats[-1].answers_central_question is True
    assert story.opening is not None
    assert story.opening.situation
    assert story.opening.first_available_actions


def test_compiler_uses_only_transport_protocol_and_parses_local_contract():
    class StubCompilerModel:
        def generate(self, prompt: str) -> str:
            assert "COMPILED_STORY_JSON" in prompt
            return json.dumps(_story_payload())

    story = CompiledStoryCompiler(StubCompilerModel()).compile(
        outline="A crew must save a beacon.", genre_profile={"genre": "sci-fi", "tone": "tense"}
    )

    assert story.id == "harbor_signal"


def test_live_compilation_is_explicitly_opt_in(monkeypatch: pytest.MonkeyPatch):
    fixture_root = Path("data/compiled_stories/v1")
    monkeypatch.delenv("FREYTAG_ENABLE_LIVE_COMPILER", raising=False)

    with pytest.raises(CompilationError, match="LIVE_COMPILATION_DISABLED"):
        CompiledStoryCompiler(None, fixture_root=fixture_root).compile_live("outline", {"genre": "fantasy"})


def test_compiler_failures_are_typed_at_transport_and_fixture_boundaries(tmp_path: Path):
    class InvalidJsonTransport:
        def generate(self, prompt: str) -> str:
            return "not json"

    with pytest.raises(CompilationError, match="COMPILER_TRANSPORT_UNAVAILABLE"):
        CompiledStoryCompiler(None).compile("outline", {"genre": "fantasy"})
    with pytest.raises(CompilationError, match="COMPILER_OUTPUT_INVALID"):
        CompiledStoryCompiler(InvalidJsonTransport()).compile("outline", {"genre": "fantasy"})
    with pytest.raises(CompilationError, match="FIXTURE_NOT_FOUND"):
        load_compiled_story_fixture("missing", tmp_path)

    malformed = tmp_path / "fantasy.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(CompilationError, match="FIXTURE_INVALID"):
        load_compiled_story_fixture("fantasy", tmp_path)


def test_runtime_fixture_map_failures_are_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/compiled_stories/v2").mkdir(parents=True)
    manifest = tmp_path / "data/compiled_stories/v2/runtime-fixtures.json"
    manifest.write_text("{", encoding="utf-8")
    with pytest.raises(CompilationError, match="FIXTURE_MAP_INVALID"):
        load_compiled_story_fixture("mystery")

    manifest.write_text(
        json.dumps({"schema_version": "runtime-fixture-map-v1", "fixtures": {"mystery": "missing.reviewed.json"}}),
        encoding="utf-8",
    )
    with pytest.raises(CompilationError, match="FIXTURE_NOT_FOUND"):
        load_compiled_story_fixture("mystery")


def test_unlocks_and_duplicate_beat_ids_are_locally_validated():
    duplicate = _story_payload()
    duplicate["beats"].append(deepcopy(duplicate["beats"][0]))
    with pytest.raises(CompilationError, match="DUPLICATE_ID"):
        validate_compiled_story(duplicate)

    unknown_unlock = _story_payload()
    unknown_unlock["beats"][0]["unlocks"] = ["missing"]
    with pytest.raises(CompilationError, match="UNKNOWN_REFERENCE"):
        validate_compiled_story(unknown_unlock)
