"""Phase 0 characterization for the offline storylet compiler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.authoring.sources import StorySourceLoader
from storygame.runtime.context import RuntimeContextBuilder
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import bootstrap_runtime_state

FIXTURE_PATH = Path("tests/fixtures/storylet_compiler_phase0.json")
BASELINE_PATH = Path("data/story_blueprints/diagnostics/storylet-compiler-phase0-baseline.json")
GENRES = ("mystery", "fantasy", "sci-fi", "relationship")


class StubModel:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.calls: list[bool] = []

    def play_turn(self, context: object, *, json_object: bool) -> object:
        self.calls.append(json_object)
        return self.responses.pop(0)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _turn(*, material_progress: bool) -> dict[str, object]:
    return {
        "narration": "A bounded consequence follows the player's attempt.",
        "operations": [],
        "beat_updates": [],
        "material_progress": material_progress,
    }


def test_phase0_cross_genre_vocabulary_covers_the_required_storylet_cases() -> None:
    fixtures = _load(FIXTURE_PATH)

    assert tuple(fixtures["genres"]) == GENRES
    for scenario in fixtures["scenarios"].values():
        eligible = scenario["eligible_situations"]
        assert len(eligible) >= 2
        assert len({item["id"] for item in eligible}) == len(eligible)
        assert len({item["purpose"] for item in eligible}) >= 2
        assert scenario["freeform_action"] not in {item["id"] for item in eligible}
        assert scenario["protected_knowledge"]["truth_id"]
        assert scenario["protected_knowledge"]["withhold_until"]
        failure_forward = scenario["failure_forward"]
        assert failure_forward["failed_storylet_id"] != failure_forward["alternative_storylet_id"]
        assert scenario["non_repetition"]["completion_fact"]


def test_phase0_selects_an_authored_vertical_slice_and_existing_reviewed_fixture() -> None:
    selection = _load(FIXTURE_PATH)["vertical_slice"]
    loader = StorySourceLoader(Path("data/story_outlines.yaml"), Path("data/genre_profiles"))
    brief = loader.load_brief(Path(selection["authoring_brief_path"]))
    reviewed = load_compiled_story_fixture(selection["reviewed_fixture_genre"])

    assert brief.creative_direction["dramatic_beats"]
    assert brief.creative_direction["possibility_library"]
    assert any("approved" in note.lower() for note in brief.creative_direction["author_notes"])
    assert reviewed.id == selection["reviewed_story_id"]


@pytest.mark.parametrize("genre", GENRES)
def test_phase0_records_runtime_baseline_without_golden_prose_assertions(genre: str) -> None:
    baseline = _load(BASELINE_PATH)["genres"][genre]
    state = bootstrap_runtime_state(load_compiled_story_fixture(genre))
    context = RuntimeContextBuilder().build(state, "Attempt a free-form story move.")
    model = StubModel([_turn(material_progress=True), _turn(material_progress=False)])
    engine = RuntimeEngine(state, model)

    first = engine.turn("Attempt a free-form story move.")
    second = engine.turn("Try a different free-form story move.")

    assert context.token_estimate == baseline["runtime_context_tokens"]
    assert model.calls == baseline["normal_turn_json_modes"]
    assert [first.model_calls, second.model_calls] == baseline["normal_turn_provider_calls"]
    assert (int(first.ok) + int(second.ok)) / 2 == baseline["successful_turn_rate"]
    assert baseline["material_progress_rate"] == 1 / 2
    assert len(state.active_beats) == baseline["active_beat_behavior"]["initial_count"]
    assert len(engine.state.active_beats) == baseline["active_beat_behavior"]["after_freeform_turns_count"]
    assert baseline["active_beat_behavior"]["requires_declared_completion_tag"]
    assert all(sample["narration"] for sample in baseline["narrative_samples"])
