from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.observation import ObservationRequest, build_observation_context
from storygame.runtime.observation_verifier import ObservationVerifier, relations_from_context
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_observation_enforcement import _ScriptedProvider
from tests.test_observation_mode import _state_at
from tests.test_observation_preview import _set_raw, _synthetic_package, _synthetic_provider

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _answers(monkeypatch: pytest.MonkeyPatch, answers: dict[str, bool | None], calls: list[str]):
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["drawer"], "same_as": {}},
    )

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        calls.extend(questions)
        return {key: {"noul": 1.0 if answers[key] else 0.0} for key in questions if answers.get(key) is not None}

    return ask


def _real_drawer_context(kind: str):
    state = _state_at("kitchen")
    world = world_for(PACKAGE, state.facts)
    assert world.set_axis("michelle_drawer", "open").ok
    assert world.reveal("memory_card").ok
    assert world.move("memory_card", "kristin").ok
    return world, build_observation_context(
        world,
        "kristin",
        ObservationRequest("Search beneath the drawer.", kind, "michelle_drawer"),
    )


def _capture_real(monkeypatch: pytest.MonkeyPatch, command: str, answers: dict[str, bool | None]):
    calls: list[str] = []
    state = _state_at("kitchen")
    provider = build_capture_provider(state)
    record = WorldCapture(provider, _answers(monkeypatch, answers, calls)).before_turn(command)
    return record, provider, calls


def test_real_capture_under_scope_does_not_require_drawer_supplies(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    state = _state_at("kitchen")
    world = world_for(PACKAGE, state.facts)
    assert world.set_axis("michelle_drawer", "open").ok
    assert world.reveal("memory_card").ok
    assert world.move("memory_card", "kristin").ok
    provider = build_capture_provider(state)
    provider._referred_names = ["drawer"]
    ask = _answers(monkeypatch, {"opens_container": False, "searches_underneath": True}, calls)
    capture = WorldCapture(provider, ask)
    capture._set_observation_request("Search beneath the drawer.", SimpleNamespace(vehicle_id=None), capture.ask)

    context = build_observation_context(world, "kristin", provider.observation_request)
    assert provider.observation_request == ObservationRequest("Search beneath the drawer.", "under", "michelle_drawer")
    assert context.required == ()
    assert {thing.name for thing in context.visible_things} >= {"binder clips", "pens", "spare batteries", "stapler"}
    assert relations_from_context(context) == ()


def test_real_under_scope_does_not_require_drawer_supplies() -> None:
    world, context = _real_drawer_context("under")

    assert context.required == ()
    assert {thing.name for thing in context.visible_things} >= {"binder clips", "pens", "spare batteries", "stapler"}
    assert relations_from_context(context) == ()


def test_real_false_under_answer_keeps_look_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    _record, provider, _calls = _capture_real(
        monkeypatch,
        "Search beneath the drawer.",
        {"opens_container": False, "searches_underneath": False},
    )

    assert provider.observation_request == ObservationRequest("Search beneath the drawer.", "look", "michelle_drawer")


@pytest.mark.parametrize("answer", [None])
def test_unknown_under_answer_keeps_strict_look_scope(monkeypatch: pytest.MonkeyPatch, answer: None) -> None:
    _record, provider, _calls = _capture_real(
        monkeypatch,
        "Search beneath the drawer.",
        {"opens_container": False, "searches_underneath": answer},
    )

    assert provider.observation_request == ObservationRequest("Search beneath the drawer.", "look", "michelle_drawer")


def test_under_question_is_asked_first_for_open_and_not_for_enter_or_non_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _record, provider, calls = _capture_real(monkeypatch, "Open the drawer.", {"opens_container": True})
    assert provider.observation_request is not None
    assert provider.observation_request.kind == "open"
    assert calls == ["searches_underneath", "opens_container"]

    state = _state_at("outside_house")
    provider = build_capture_provider(state)
    calls = []
    ask = _answers(monkeypatch, {"searches_underneath": True}, calls)
    WorldCapture(provider, ask)._set_observation_request(
        "Enter the truck.", SimpleNamespace(vehicle_id="kristin_truck"), ask
    )
    assert provider.observation_request is not None
    assert provider.observation_request.kind == "enter"
    assert calls == []

    state = _state_at("kitchen")
    provider = build_capture_provider(state)
    calls = []
    ask = _answers(monkeypatch, {"searches_underneath": True}, calls)
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["kitchen table"], "same_as": {}},
    )
    provider._referred_names = ["kitchen"]
    WorldCapture(provider, ask)._set_observation_request(
        "Look beneath the kitchen.", SimpleNamespace(vehicle_id=None), ask
    )
    assert provider.observation_request is not None
    assert provider.observation_request.kind == "look"
    assert calls == []


def test_supporter_under_scope_is_optional_only_for_under_search(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at("outside_house", already_aboard=True)
    provider = build_capture_provider(state)
    calls: list[str] = []
    provider._referred_names = ["passenger seat"]

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        calls.extend(questions)
        return {key: {"noul": 1.0} for key in questions}

    capture = WorldCapture(provider, ask)
    capture._set_observation_request("Search beneath the passenger seat.", SimpleNamespace(vehicle_id=None), ask)
    assert provider.observation_request == ObservationRequest(
        "Search beneath the passenger seat.", "under", "truck_passenger_seat"
    )
    world = world_for(PACKAGE, state.facts)
    context = build_observation_context(world, "kristin", provider.observation_request)
    assert context.required == ()
    assert "Kristin's laptop" in {thing.name for thing in context.visible_things}

    provider.observation_request = None
    provider._referred_names = ["passenger seat"]

    def false_ask(*_args: object) -> dict[str, dict[str, float]]:
        return {"searches_underneath": {"noul": 0.0}}

    WorldCapture(provider, false_ask)._set_observation_request(
        "Search beneath the passenger seat.", SimpleNamespace(vehicle_id=None), false_ask
    )
    assert provider.observation_request is not None
    assert provider.observation_request.kind == "look"


def test_visible_under_item_is_required_but_hidden_under_item_is_not() -> None:
    state = _state_at("kitchen")
    package = state.package
    world = world_for(package, state.facts)
    assert world.set_axis("michelle_drawer", "open").ok
    assert world.move("michelle_drawer_binder_clips", "michelle_drawer", under=True).ok
    context = build_observation_context(
        world, "kristin", ObservationRequest("Search beneath the drawer.", "under", "michelle_drawer")
    )
    assert context.required == ("binder clips",)
    assert "Michelle's memory card" not in {thing.name for thing in context.visible_things}


def test_second_story_keeps_under_scope_independent() -> None:
    package = _synthetic_package()
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    under = build_observation_context(
        world, "hero", ObservationRequest("Feel beneath the survey tray.", "under", "tray")
    )
    look = build_observation_context(world, "hero", ObservationRequest("Inspect the survey tray.", "look", "tray"))
    assert under.required == ()
    assert look.required == ("calibrated lens",)

    assert world.move("lens", "tray", under=True).ok
    under = build_observation_context(
        world, "hero", ObservationRequest("Feel beneath the survey tray.", "under", "tray")
    )
    assert under.required == ("calibrated lens",)


def test_under_turn_has_no_observation_verifier_relations_and_keeps_unrelated_move_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["drawer"], "same_as": {}},
    )
    state = _state_at("kitchen")
    provider = _ScriptedProvider(state, [("The underside is clear.", None)])
    provider.observe_automatically = True
    asks: list[object] = []

    def ask(_state: object, questions: object) -> dict[str, dict[str, float]]:
        asks.append(questions)
        return {key: {"noul": 1.0 if key == "searches_underneath" else 0.0} for key in questions}

    capture = WorldCapture(provider, ask)
    capture.enforcing_verifier = ObservationVerifier(capture.ask)
    result = RuntimeEngine(state, provider, capture=capture).turn("Search beneath the drawer.")

    assert result.narration == "The underside is clear."
    assert provider.observation_request == ObservationRequest("Search beneath the drawer.", "under", "michelle_drawer")
    assert provider.rejections == []
    assert any(isinstance(item, dict) and "searches_underneath" in item for item in asks)

    state, provider = _synthetic_provider()
    provider.observation_request = ObservationRequest("Search beneath the survey tray.", "under", "tray")
    capture = WorldCapture(provider, ask)
    capture.enforcing_verifier = ObservationVerifier(capture.ask)
    _set_raw(provider, {"remote marker": {"place": "the far field"}})
    candidate = copy.deepcopy(state)
    preview = capture.preview_commit(
        "Search beneath the survey tray.", "The underside is clear.", candidate, entered_scene=False
    )

    assert preview.accepted is False
    assert preview.outcome == "unrelated_move"


def test_unrecovered_card_stays_hidden_on_an_under_search() -> None:
    state = _state_at("kitchen")
    world = world_for(PACKAGE, state.facts)
    assert world.set_axis("michelle_drawer", "open").ok
    assert world.is_hidden("memory_card")

    context = build_observation_context(
        world,
        "kristin",
        ObservationRequest("Search beneath the drawer.", "under", "michelle_drawer"),
    )

    assert context.required == ()
    assert relations_from_context(context) == ()
    assert "memory card" not in " ".join(
        thing.name.casefold() for thing in (*context.visible_things, *context.contingent_things)
    )
