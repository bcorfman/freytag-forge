from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from storygame.runtime.observation import (
    ObservationContext,
    ObservationRequest,
    ObservedThing,
    build_observation_context,
)
from storygame.runtime.observation_verifier import ObservationVerifier, Relation, relations_from_context
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ItemPlacement
from tests.test_observation_preview import _synthetic_package
from tests.test_web_demo_observation_enforce import _app, _record_captures, _session

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
PROBE_PATH = ROOT / "scripts/ringer/environment_narration/j1c_wiring_probe.py"
PROBE_SPEC = importlib.util.spec_from_file_location("j1c_wiring_probe", PROBE_PATH)
assert PROBE_SPEC is not None and PROBE_SPEC.loader is not None
j1c_wiring_probe = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(j1c_wiring_probe)


def _ask(calls: list[tuple[object, object]]):
    def ask(state, questions):
        calls.append((state, questions))
        return {key: {"noul": 1.0} for key in questions}

    return ask


def _relations(*relations: Relation) -> tuple[Relation, ...]:
    return tuple(relations)


def test_scene_level_state_has_only_scene_level_starting_places() -> None:
    calls = []
    verifier = ObservationVerifier(_ask(calls), scene_state=True)

    verifier.verify("A drain is visible.", _relations(Relation("drain", "street", scene_level=True)), scene="Street")

    assert calls[0][0] == {
        "narration": "A drain is visible.",
        "scene": "Street",
        "starting_places": {"drain": "street"},
    }


def test_non_scene_relation_uses_v0_state_and_keeps_questions() -> None:
    relation = Relation("key", "drawer")
    off_calls = []
    on_calls = []

    ObservationVerifier(_ask(off_calls)).verify("A key is mentioned.", (relation,), scene="Room")
    ObservationVerifier(_ask(on_calls), scene_state=True).verify("A key is mentioned.", (relation,), scene="Room")

    assert off_calls[0][0] == {"narration": "A key is mentioned."}
    assert on_calls[0][0] == {"narration": "A key is mentioned."}
    assert on_calls[0][1] == off_calls[0][1]


def test_held_relation_is_never_scene_level() -> None:
    context = ObservationContext(
        observer="Ari",
        action="look",
        completed_actions=(),
        visible_things=(ObservedThing("key", "Ari", "Ari", True),),
        contingent_things=(),
        required=("key",),
        omitted_optional=(),
        scope_complete=False,
        scene="Room",
    )

    assert relations_from_context(context) == (Relation("key"),)


def test_flag_off_sends_v0_state_for_scene_level_relation() -> None:
    calls = []
    report = ObservationVerifier(_ask(calls)).verify(
        "A drain is visible.", (Relation("drain", "street", scene_level=True),), scene="Street"
    )

    assert calls[0][0] == {"narration": "A drain is visible."}
    assert report.scene_state is False


def test_mixed_batch_sends_only_scene_level_entries() -> None:
    calls = []
    verifier = ObservationVerifier(_ask(calls), scene_state=True)

    verifier.verify(
        "The drain and key are visible.",
        _relations(
            Relation("drain", "street", scene_level=True),
            Relation("key", "drawer"),
            Relation("sign", "street", scene_level=True),
        ),
        scene="Street",
    )

    assert calls[0][0] == {
        "narration": "The drain and key are visible.",
        "scene": "Street",
        "starting_places": {"drain": "street", "sign": "street"},
    }


def test_question_text_is_identical_with_scene_state_flag() -> None:
    relation = Relation("drain", "street", scene_level=True)
    off_calls = []
    on_calls = []

    ObservationVerifier(_ask(off_calls)).verify("The drain is visible.", (relation,), scene="Street")
    ObservationVerifier(_ask(on_calls), scene_state=True).verify("The drain is visible.", (relation,), scene="Street")

    assert on_calls[0][1] == off_calls[0][1]


def test_report_scene_state_is_true_only_when_j1c_state_was_sent() -> None:
    relation = Relation("drain", "street", scene_level=True)
    assert ObservationVerifier(_ask([]), scene_state=True).verify("text", (relation,), scene="Street").scene_state
    assert not ObservationVerifier(_ask([]), scene_state=True).verify("text", (relation,)).scene_state
    assert not ObservationVerifier(_ask([])).verify("text", (relation,), scene="Street").scene_state
    assert not ObservationVerifier(_ask([]), scene_state=True).verify("text", ()).scene_state


def test_build_observation_context_marks_direct_scene_items_only() -> None:
    package = _synthetic_package()
    scene = package.scenes[0]
    metadata = scene.metadata.model_copy(
        update={"item_placements": {**scene.metadata.item_placements, "remote_marker": ItemPlacement(parent="room")}}
    )
    package = package.model_copy(update={"scenes": (scene.model_copy(update={"metadata": metadata}),)})
    state = RuntimeState.bootstrap(package)
    apply_scene_placements(package, state.facts, "1A")
    world = world_for(package, state.facts)

    direct = build_observation_context(
        world,
        "hero",
        ObservationRequest("Look at the marker.", "look", "remote_marker"),
        scene_location_id="room",
    )
    nested = build_observation_context(
        world,
        "hero",
        ObservationRequest("Look at the tray.", "look", "tray"),
        scene_location_id="room",
    )

    assert direct.scene == "the room"
    assert direct.visible_things[0].scene_level is True
    assert nested.visible_things[0].scene_level is False


def test_state_matches_j1c_wiring_probe() -> None:
    relations = _relations(
        Relation("drain", "street", scene_level=True),
        Relation("key", "drawer"),
        Relation("sign", "street", scene_level=True),
    )
    calls = []
    ObservationVerifier(_ask(calls), scene_state=True).verify("The facts.", relations, scene="Street")
    items = [(relation.thing, relation.place, relation.scene_level) for relation in relations]

    assert calls[0][0] == j1c_wiring_probe.j1c_state("The facts.", items, "Street")


def test_continuity_scene_places_storm_drain_directly_in_its_location() -> None:
    scene = next(scene for scene in PACKAGE.scenes if "storm_drain" in scene.metadata.item_ids)
    state = RuntimeState.bootstrap(PACKAGE)
    apply_scene_placements(PACKAGE, state.facts, scene.metadata.scene_id)

    assert world_for(PACKAGE, state.facts).parent("storm_drain") == scene.metadata.location_id


@pytest.mark.parametrize("scene_flag", [False, True])
def test_web_demo_wires_scene_state_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scene_flag: bool) -> None:
    monkeypatch.setenv("FREYTAG_OBSERVATION_ENFORCE", "1")
    if scene_flag:
        monkeypatch.setenv("FREYTAG_OBSERVATION_SCENE_STATE", "1")
    else:
        monkeypatch.delenv("FREYTAG_OBSERVATION_SCENE_STATE", raising=False)
    captures = _record_captures(monkeypatch)

    with TestClient(_app(monkeypatch, tmp_path)) as client:
        _session(client)

    assert captures[-1].enforcing_verifier.scene_state is scene_flag
