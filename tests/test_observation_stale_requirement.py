from __future__ import annotations

import copy

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from tests.test_observation_enforcement import (
    _capture as enforcement_capture,
)
from tests.test_observation_enforcement import (
    _observing_provider,
    _observing_state,
    _ScriptedProvider,
)
from tests.test_observation_preview import _synthetic_package
from tests.test_observation_shadow import _capture as shadow_capture
from tests.test_observation_shadow import _provider as shadow_provider


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _scene_phase(state: RuntimeState, scene_id: str) -> str:
    return next(scene.metadata.freytag_phase for scene in state.package.scenes if scene.metadata.scene_id == scene_id)


def _prepare_shadow():
    state, provider = shadow_provider()
    provider.observe_automatically = False
    calls: list[tuple[object, object]] = []

    def ask(verifier_state, questions):
        calls.append((verifier_state, questions))
        return {key: {"noul": 1.0} for key in questions}

    capture = shadow_capture(provider, ObservationVerifier(ask))
    capture.before_turn("Inspect the truck.")
    return state, provider, capture, calls


def _assert_dropped_shadow(record: dict[str, object], calls: list[object]) -> None:
    shadow = record["observation_shadow"]
    assert shadow["outcome"] == "no_relations"
    assert shadow["requests"] == 0
    assert shadow["accepted"] is True
    assert shadow["verdicts"] == []
    assert shadow["requirement_dropped"] == "scene_or_area_changed"
    assert not [item for item in calls if isinstance(item[1], dict) and "relation_0" in item[1]]


def test_shadow_drops_requirement_when_turn_enters_new_scene() -> None:
    state, _provider, capture, calls = _prepare_shadow()
    state.current_scene_id = "1B"
    state.phase = _scene_phase(state, "1B")

    record = capture.after_commit("Inspect the truck.", "The new place is quiet.", entered_scene=True)

    _assert_dropped_shadow(record, calls)


def test_shadow_drops_requirement_when_protagonist_changes_area() -> None:
    state, provider, capture, calls = _prepare_shadow()
    protagonist_id = state.package.world.protagonist_id
    assert provider._world().place(protagonist_id, "kitchen").ok

    record = capture.after_commit("Inspect the truck.", "The new place is quiet.", entered_scene=False)

    _assert_dropped_shadow(record, calls)


def test_shadow_still_verifies_an_ordinary_same_area_turn_in_synthetic_story() -> None:
    state = RuntimeState.bootstrap(_synthetic_package())
    provider = _ScriptedProvider(state, [("The calibrated lens catches the light.", None)])
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Inspect the survey tray.", "look", "tray")
    calls: list[tuple[object, object]] = []

    def ask(verifier_state, questions):
        calls.append((verifier_state, questions))
        return {key: {"noul": 1.0} for key in questions}

    capture = WorldCapture(provider, ask)
    capture.shadow_verifier = ObservationVerifier(ask)
    capture.before_turn("Inspect the survey tray.")
    record = capture.after_commit(
        "Inspect the survey tray.", "The calibrated lens catches the light.", entered_scene=False
    )

    shadow = record["observation_shadow"]
    assert shadow["outcome"] == "ok"
    assert shadow["requests"] == 1
    assert shadow["accepted"] is True
    assert "requirement_dropped" not in shadow
    assert len([item for item in calls if "relation_0" in item[1]]) == 1


def test_enforcement_preview_drops_stale_requirement_but_keeps_unrelated_move_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _observing_state()
    provider = _observing_provider(state, [("The new place is quiet.", None)])
    capture, asks = enforcement_capture(provider, [1.0])
    command = "Inspect the truck."
    capture.before_turn(command)
    provider(command)

    accepted = capture.preview_commit(command, "The new place is quiet.", copy.deepcopy(state), entered_scene=True)

    assert accepted.accepted is True
    assert accepted.verdicts == ()
    assert not [item for item in asks if isinstance(item[1], dict) and "relation_0" in item[1]]

    moved_state = _observing_state()
    moved_provider = _observing_provider(
        moved_state,
        [("The new place is quiet.", {"notebook": {"place": "kitchen"}})],
    )
    moved_capture, moved_asks = enforcement_capture(moved_provider, [1.0])
    moved_capture.before_turn(command)
    moved_provider(command)

    def move_pre_existing_item(*_args, **_kwargs):
        assert moved_provider._world().move("kristin_laptop", "kitchen").ok
        moved_provider._changed_last_turn.add("kristin_laptop")
        return None, []

    monkeypatch.setattr(moved_provider, "apply_item_facts", move_pre_existing_item)
    candidate = copy.deepcopy(moved_state)
    assert world_for(candidate.package, candidate.facts).move("kristin", "kitchen").ok

    rejected = moved_capture.preview_commit(
        command,
        "The new place is quiet.",
        candidate,
        entered_scene=False,
    )

    assert rejected.accepted is False
    assert rejected.outcome == "unrelated_move"
    assert rejected.failure == "unrelated_move"
    assert rejected.moved_unrelated
    assert not [item for item in moved_asks if isinstance(item[1], dict) and "relation_0" in item[1]]


def test_before_turn_resets_origin_after_a_stale_turn() -> None:
    state, _provider, capture, calls = _prepare_shadow()
    state.current_scene_id = "1B"
    state.phase = _scene_phase(state, "1B")
    first = capture.after_commit("Inspect the truck.", "The new place is quiet.", entered_scene=True)
    assert first["observation_shadow"]["requirement_dropped"] == "scene_or_area_changed"

    state.current_scene_id = "1A"
    state.phase = _scene_phase(state, "1A")
    assert world_for(state.package, state.facts).place(state.package.world.protagonist_id, "truck_driver_seat").ok
    capture.before_turn("Inspect the truck.")
    second = capture.after_commit("Inspect the truck.", "The observed details remain unchanged.", entered_scene=False)

    shadow = second["observation_shadow"]
    assert shadow["outcome"] == "ok"
    assert shadow["requests"] == 1
    assert shadow["accepted"] is True
    assert "requirement_dropped" not in shadow
    assert len([item for item in calls if "relation_0" in item[1]]) == 1


def test_default_path_with_shadow_and_enforcement_off_keeps_record_shape() -> None:
    state = RuntimeState.bootstrap(_synthetic_package())
    provider = _ScriptedProvider(state, [("The far field is quiet.", None)])
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Inspect the survey tray.", "look", "tray")
    calls: list[tuple[object, object]] = []
    capture = WorldCapture(provider, lambda verifier_state, questions: calls.append((verifier_state, questions)) or {})
    capture.before_turn("Inspect the survey tray.")
    state.current_scene_id = "1A"

    record = capture.after_commit("Inspect the survey tray.", "The far field is quiet.", entered_scene=False)

    assert "observation_shadow" not in record
    assert "observation_preview" not in record
    assert not [item for item in calls if isinstance(item[1], dict) and "relation_0" in item[1]]
