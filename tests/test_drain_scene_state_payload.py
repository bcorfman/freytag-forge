"""A stub proves scene-state payload wiring only, not verifier quality."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.observation import ObservationRequest, build_observation_context
from storygame.runtime.observation_verifier import ObservationVerifier, Relation, relations_from_context
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ItemPlacement
from tests.test_observation_enforcement import _ScriptedProvider
from tests.test_observation_preview import _synthetic_package

ROOT = Path(__file__).parents[1]
CONTINUITY_PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


@dataclass(frozen=True)
class _PayloadCase:
    name: str
    narration: str
    relations: tuple[Relation, ...]
    scene: str
    expected_off: dict[str, object]
    expected_on: dict[str, object]
    score: float


def _continuity_drain() -> tuple[Relation, str]:
    scene = next(scene for scene in CONTINUITY_PACKAGE.scenes if "storm_drain" in scene.metadata.item_ids)
    state = RuntimeState.bootstrap(CONTINUITY_PACKAGE)
    apply_scene_placements(CONTINUITY_PACKAGE, state.facts, scene.metadata.scene_id)
    world = world_for(CONTINUITY_PACKAGE, state.facts)
    context = build_observation_context(
        world,
        CONTINUITY_PACKAGE.world.protagonist_id,
        ObservationRequest("Inspect the storm drain.", "look", "storm_drain"),
        scene_location_id=scene.metadata.location_id,
    )
    return relations_from_context(context)[0], context.scene or ""


def _synthetic_scene_object() -> tuple[Relation, str]:
    package = _synthetic_package()
    scene = package.scenes[0]
    metadata = scene.metadata.model_copy(
        update={"item_placements": {**scene.metadata.item_placements, "remote_marker": ItemPlacement(parent="room")}}
    )
    package = package.model_copy(update={"scenes": (scene.model_copy(update={"metadata": metadata}),)})
    state = RuntimeState.bootstrap(package)
    apply_scene_placements(package, state.facts, scene.metadata.scene_id)
    world = world_for(package, state.facts)
    context = build_observation_context(
        world,
        "hero",
        ObservationRequest("Inspect the remote marker.", "look", "remote_marker"),
        scene_location_id="room",
    )
    return relations_from_context(context)[0], context.scene or ""


_DRAIN, _DRAIN_SCENE = _continuity_drain()
_SYNTHETIC_SCENE_OBJECT, _SYNTHETIC_SCENE = _synthetic_scene_object()

_PAYLOAD_CASES = (
    _PayloadCase(
        "continuity_drain",
        "The storm drain is visible beneath the path.",
        (_DRAIN,),
        _DRAIN_SCENE,
        {"narration": "The storm drain is visible beneath the path."},
        {
            "narration": "The storm drain is visible beneath the path.",
            "scene": "Los Angeles park",
            "starting_places": {"storm drain": "Los Angeles park"},
        },
        1.0,
    ),
    _PayloadCase(
        "different_story_scene_object",
        "The remote marker is visible in the room.",
        (_SYNTHETIC_SCENE_OBJECT,),
        _SYNTHETIC_SCENE,
        {"narration": "The remote marker is visible in the room."},
        {
            "narration": "The remote marker is visible in the room.",
            "scene": "the room",
            "starting_places": {"remote marker": "the room"},
        },
        1.0,
    ),
    _PayloadCase(
        "specific_place",
        "The calibrated lens rests in the survey tray.",
        (Relation("calibrated lens", "survey tray"),),
        "the room",
        {"narration": "The calibrated lens rests in the survey tray."},
        {"narration": "The calibrated lens rests in the survey tray."},
        1.0,
    ),
    _PayloadCase(
        "held_object",
        "Ari holds the calibrated lens.",
        (Relation("calibrated lens"),),
        "the room",
        {"narration": "Ari holds the calibrated lens."},
        {"narration": "Ari holds the calibrated lens."},
        1.0,
    ),
    _PayloadCase(
        "mixed_scene_and_held",
        "The storm drain is visible, and Ari holds the lens.",
        (_DRAIN, Relation("calibrated lens")),
        _DRAIN_SCENE,
        {"narration": "The storm drain is visible, and Ari holds the lens."},
        {
            "narration": "The storm drain is visible, and Ari holds the lens.",
            "scene": "Los Angeles park",
            "starting_places": {"storm drain": "Los Angeles park"},
        },
        1.0,
    ),
    _PayloadCase(
        "explicit_moved_away_negative",
        "The storm drain has been moved to the alley.",
        (_DRAIN,),
        _DRAIN_SCENE,
        {"narration": "The storm drain has been moved to the alley."},
        {
            "narration": "The storm drain has been moved to the alley.",
            "scene": "Los Angeles park",
            "starting_places": {"storm drain": "Los Angeles park"},
        },
        0.0,
    ),
)


def _ask(calls: list[tuple[object, object]], score: float):
    def ask(state: object, questions: object) -> dict[str, dict[str, float]]:
        calls.append((state, questions))
        assert isinstance(questions, dict)
        return {key: {"noul": score} for key in questions}

    return ask


@pytest.fixture(params=(False, True), ids=("scene-state-off", "scene-state-on"))
def scene_state(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.fixture(params=_PAYLOAD_CASES, ids=lambda case: case.name)
def payload_case(request: pytest.FixtureRequest) -> _PayloadCase:
    return request.param


def test_scene_state_payload_matrix(payload_case: _PayloadCase, scene_state: bool) -> None:
    calls: list[tuple[object, object]] = []
    verifier = ObservationVerifier(_ask(calls, payload_case.score), scene_state=scene_state)

    report = verifier.verify(payload_case.narration, payload_case.relations, scene=payload_case.scene)

    assert len(calls) == 1
    assert calls[0][0] == (payload_case.expected_on if scene_state else payload_case.expected_off)
    assert report.accepted is (payload_case.score > 0.65)


def _question_bytes(question: object) -> bytes:
    return json.dumps(question, sort_keys=True, separators=(",", ":")).encode("utf-8")


@pytest.mark.parametrize("payload_case", _PAYLOAD_CASES, ids=lambda case: case.name)
def test_non_scene_questions_are_byte_identical_between_modes(payload_case: _PayloadCase) -> None:
    off_calls: list[tuple[object, object]] = []
    on_calls: list[tuple[object, object]] = []
    ObservationVerifier(_ask(off_calls, payload_case.score), scene_state=False).verify(
        payload_case.narration, payload_case.relations, scene=payload_case.scene
    )
    ObservationVerifier(_ask(on_calls, payload_case.score), scene_state=True).verify(
        payload_case.narration, payload_case.relations, scene=payload_case.scene
    )

    off_questions = off_calls[0][1]
    on_questions = on_calls[0][1]
    assert isinstance(off_questions, dict)
    assert isinstance(on_questions, dict)
    for index, relation in enumerate(payload_case.relations):
        if not relation.scene_level:
            key = f"relation_{index}"
            assert _question_bytes(on_questions[key]) == _question_bytes(off_questions[key])


@pytest.mark.parametrize(
    ("score", "expected_verdict"),
    ((0.65, "uncertain"), (0.35, "uncertain"), (0.66, "accept"), (0.34, "reject")),
)
def test_scene_state_keeps_strict_verdict_thresholds(score: float, expected_verdict: str) -> None:
    calls: list[tuple[object, object]] = []
    report = ObservationVerifier(_ask(calls, score), scene_state=True).verify(
        "The storm drain is visible.", (_DRAIN,), scene=_DRAIN_SCENE
    )

    assert report.verdicts[0].verdict == expected_verdict


def test_unrelated_parent_move_rejects_with_scene_state_enabled() -> None:
    state = RuntimeState.bootstrap(_synthetic_package())
    provider = _ScriptedProvider(
        state,
        [("The calibrated lens catches the light.", {"remote marker": {"place": "the far field"}})],
    )
    provider._pending_item_facts = {"remote marker": {"place": "the far field"}}
    provider._pending_item_facts_present = True
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Inspect the survey tray.", "look", "tray")
    calls: list[tuple[object, object]] = []
    capture = WorldCapture(provider, _ask(calls, 1.0))
    capture.enforcing_verifier = ObservationVerifier(capture.ask, scene_state=True)

    result = capture.preview_commit(
        "Inspect the survey tray.",
        "The calibrated lens catches the light.",
        copy.deepcopy(state),
        entered_scene=False,
    )

    assert result.accepted is False
    assert result.outcome == "unrelated_move"
    assert result.failure == "unrelated_move"
    assert result.moved_unrelated == ("remote marker",)
