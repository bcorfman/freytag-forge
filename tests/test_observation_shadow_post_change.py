from __future__ import annotations

import copy

import pytest

import storygame.runtime.capture as capture_module
from storygame.runtime.capture import WorldCapture
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_verifier import ObservationVerifier, Relation
from storygame.runtime.world_model import world_for
from tests.test_observation_preview import _set_raw, _synthetic_provider
from tests.test_observation_stale_requirement import (
    _assert_dropped_shadow,
    _prepare_shadow,
    _scene_phase,
)


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _post_change_case():
    state, provider = _synthetic_provider()
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Lift the calibrated lens from the survey tray.", "look", "lens")
    _set_raw(provider, {"calibrated lens": {"held_by": "Ari"}})
    calls: list[tuple[object, object]] = []

    def ask(verifier_state, questions):
        calls.append((verifier_state, questions))
        return {key: {"noul": 1.0} for key in questions}

    capture = WorldCapture(provider, ask)
    return state, provider, capture, calls


def _capture_relations(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Relation, ...]]:
    captured: list[tuple[Relation, ...]] = []
    original = capture_module.relations_from_context

    def wrapped(context):
        relations = original(context)
        captured.append(relations)
        return relations

    monkeypatch.setattr(capture_module, "relations_from_context", wrapped)
    return captured


def test_shadow_relations_use_post_change_held_item_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    state, provider, capture, _calls = _post_change_case()
    captured = _capture_relations(monkeypatch)
    capture.shadow_verifier = ObservationVerifier(capture.ask)

    record = capture.after_commit(
        "Lift the calibrated lens from the survey tray.",
        "Ari lifts the calibrated lens from the survey tray.",
        entered_scene=False,
    )

    assert world_for(state.package, state.facts).parent("lens") == "hero"
    assert captured == [(Relation(thing="calibrated lens"),)]
    assert record["observation_shadow"]["requests"] == 1


def test_preview_and_shadow_receive_equal_post_change_relations(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _provider, capture, _calls = _post_change_case()
    captured = _capture_relations(monkeypatch)
    capture.enforcing_verifier = ObservationVerifier(capture.ask)
    capture.shadow_verifier = ObservationVerifier(capture.ask)
    command = "Lift the calibrated lens from the survey tray."
    narration = "Ari lifts the calibrated lens from the survey tray."
    capture.before_turn(command)

    preview = capture.preview_commit(command, narration, copy.deepcopy(state), entered_scene=False)
    record = capture.after_commit(command, narration, entered_scene=False)

    assert preview.accepted is True
    assert record["observation_shadow"]["requests"] == 1
    assert captured[0] == captured[1]
    assert captured[0] == (Relation(thing="calibrated lens"),)


def test_ordinary_shadow_keeps_relations_record_shape_and_one_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    _state, _provider, capture, calls = _post_change_case()
    _set_raw(capture.provider, {})
    captured = _capture_relations(monkeypatch)
    capture.shadow_verifier = ObservationVerifier(capture.ask)

    record = capture.after_commit(
        "Lift the calibrated lens from the survey tray.",
        "The calibrated lens remains on the survey tray.",
        entered_scene=False,
    )

    assert captured == [(Relation(thing="calibrated lens", place="survey tray"),)]
    assert len([item for item in calls if isinstance(item[1], dict) and "relation_0" in item[1]]) == 1
    assert record["observation_shadow"]["requests"] == 1
    assert tuple(record) == (
        "issues",
        "unplaced",
        "refused",
        "changed",
        "raw",
        "match_info",
        "narration_prompt",
        "facts_after",
        "observation_shadow",
    )


@pytest.mark.parametrize("change", ("scene", "area"))
def test_stale_shadow_still_drops_requirement(change: str) -> None:
    state, _provider, capture, calls = _prepare_shadow()
    if change == "scene":
        state.current_scene_id = "1B"
        state.phase = _scene_phase(state, "1B")
        entered_scene = True
    else:
        protagonist_id = state.package.world.protagonist_id
        assert capture.provider._world().place(protagonist_id, "kitchen").ok
        entered_scene = False

    record = capture.after_commit("Inspect the truck.", "The new place is quiet.", entered_scene=entered_scene)

    _assert_dropped_shadow(record, calls)


def test_shadow_is_recorded_when_item_facts_return_issues() -> None:
    _state, provider, capture, _calls = _post_change_case()
    _set_raw(provider, {"calibrated lens": {}})
    capture.shadow_verifier = ObservationVerifier(capture.ask)

    record = capture.after_commit(
        "Lift the calibrated lens from the survey tray.",
        "Ari cannot lift the calibrated lens.",
        entered_scene=False,
    )

    assert record["issues"]
    assert record["observation_shadow"]["outcome"] == "ok"
    assert record["observation_shadow"]["requests"] == 1


def test_shadow_error_keeps_other_record_fields_unchanged() -> None:
    _state, provider, baseline_capture, _calls = _post_change_case()
    _set_raw(provider, {})
    baseline = baseline_capture.after_commit(
        "Lift the calibrated lens from the survey tray.",
        "The calibrated lens remains on the survey tray.",
        entered_scene=False,
    )

    _state, provider, capture, _calls = _post_change_case()
    _set_raw(provider, {})
    verifier = ObservationVerifier(capture.ask)

    def explode(_narration, _relations):
        raise LookupError("shadow failure")

    verifier.verify = explode
    capture.shadow_verifier = verifier
    record = capture.after_commit(
        "Lift the calibrated lens from the survey tray.",
        "The calibrated lens remains on the survey tray.",
        entered_scene=False,
    )

    without_shadow = {key: value for key, value in record.items() if key != "observation_shadow"}
    assert without_shadow == baseline
    assert record["observation_shadow"]["outcome"] == "shadow_error"
    assert record["observation_shadow"]["failure"] == "LookupError"


def test_shadow_and_enforcement_off_add_no_asks_or_record_fields() -> None:
    _state, provider, capture, calls = _post_change_case()
    _set_raw(provider, {})

    record = capture.after_commit(
        "Lift the calibrated lens from the survey tray.",
        "The calibrated lens remains on the survey tray.",
        entered_scene=False,
    )

    assert "observation_shadow" not in record
    assert "observation_preview" not in record
    assert calls == []
