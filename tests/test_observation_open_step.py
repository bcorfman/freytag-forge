from __future__ import annotations

import copy
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest, build_observation_context
from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_observation_enforcement import _ScriptedProvider
from tests.test_observation_mode import _state_at
from tests.test_observation_preview import _synthetic_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _ask_answers(monkeypatch: pytest.MonkeyPatch, answers: dict[str, bool | None]):
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["drawer"], "same_as": {}},
    )

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        return {key: {"noul": 1.0 if answers.get(key) else 0.0} for key in questions if answers.get(key) is not None}

    return ask


def _world_snapshot(world) -> dict[str, tuple[str | None, dict[str, str]]]:
    return {
        entity_id: (world.parent(entity_id), dict(world.axis_values(entity_id))) for entity_id in world.entity_ids()
    }


def _real_capture(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    answers: dict[str, bool | None],
    *,
    place_id: str = "kitchen",
):
    state = _state_at(place_id)
    provider = build_capture_provider(state)
    record = WorldCapture(provider, _ask_answers(monkeypatch, answers)).before_turn(command)
    return state, provider, record


def _synthetic_container_package(*, openable: bool, open: bool, hidden: bool = False):
    package = _synthetic_package()
    items = list(package.world.items)
    items[0] = items[0].model_copy(update={"kind": "container", "openable": openable, "open": open, "hidden": hidden})
    world = package.world.model_copy(update={"items": items})
    return package.model_copy(update={"world": world})


def _synthetic_capture(
    monkeypatch: pytest.MonkeyPatch,
    *,
    openable: bool,
    open: bool,
    hidden: bool = False,
):
    package = _synthetic_container_package(openable=openable, open=open, hidden=hidden)
    state = RuntimeState.bootstrap(package)
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["survey tray"], "same_as": {}},
    )

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        return {key: {"noul": 0.0 if key == "searches_underneath" else 1.0} for key in questions}

    record = WorldCapture(provider, ask).before_turn("Open the survey tray.")
    return state, provider, record


def test_open_step_changes_only_closed_real_drawer_and_updates_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at("kitchen")
    before_world = world_for(PACKAGE, state.facts)
    before = _world_snapshot(before_world)
    assert before_world.axis_values("michelle_drawer").get("open") == "closed"

    provider = build_capture_provider(state)
    record = WorldCapture(provider, _ask_answers(monkeypatch, {"opens_container": True})).before_turn(
        "Open the drawer."
    )

    after_world = world_for(PACKAGE, state.facts)
    assert after_world.axis_values("michelle_drawer").get("open") == "open"
    assert record["engine_opened"] is True
    assert record["focus_open_state_after"] == "open"
    assert {
        entity_id: facts for entity_id, facts in _world_snapshot(after_world).items() if entity_id != "michelle_drawer"
    } == {entity_id: facts for entity_id, facts in before.items() if entity_id != "michelle_drawer"}

    context = provider._observation_context()
    assert context is not None
    assert set(("binder clips", "pens", "spare batteries", "stapler")) <= set(context.required)
    prompt = provider._section_user_prompt({})
    assert "- Show these in your reply: binder clips, pens, spare batteries, stapler." in prompt
    assert "If the drawer opens" not in prompt


def test_look_inside_command_uses_the_same_open_step(monkeypatch: pytest.MonkeyPatch) -> None:
    state, provider, record = _real_capture(
        monkeypatch,
        "Look inside the drawer.",
        {"opens_container": True},
    )
    world = world_for(PACKAGE, state.facts)

    assert provider.observation_request == ObservationRequest("Look inside the drawer.", "open", "michelle_drawer")
    assert record["engine_opened"] is True
    assert record["focus_open_state_after"] == "open"
    assert world.axis_values("michelle_drawer").get("open") == "open"


@pytest.mark.parametrize(
    ("command", "answers", "place_id", "expected_kind"),
    (
        ("Open the drawer.", {"opens_container": False}, "kitchen", "look"),
        ("Open the drawer.", {"opens_container": None}, "kitchen", "look"),
        (
            "Search beneath the drawer.",
            {"opens_container": False, "searches_underneath": True},
            "kitchen",
            "under",
        ),
        (
            "Enter the truck.",
            {"boards_vehicle": True, "only_boards_vehicle": True},
            "outside_house",
            "enter",
        ),
    ),
)
def test_open_step_is_inert_for_other_answers_and_kinds(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    answers: dict[str, bool | None],
    place_id: str,
    expected_kind: str,
) -> None:
    state, provider, record = _real_capture(monkeypatch, command, answers, place_id=place_id)
    world = world_for(PACKAGE, state.facts)

    assert provider.observation_request is not None
    assert provider.observation_request.kind == expected_kind
    assert record["engine_opened"] is False
    assert record["focus_open_state_after"] in {None, "closed", "open"}
    assert world.axis_values("michelle_drawer").get("open") == "closed"


def test_open_step_is_inert_for_already_open_drawer(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at("kitchen")
    world = world_for(PACKAGE, state.facts)
    assert world.set_axis("michelle_drawer", "open").ok
    provider = build_capture_provider(state)

    record = WorldCapture(provider, _ask_answers(monkeypatch, {"opens_container": True})).before_turn(
        "Open the drawer."
    )

    assert record["engine_opened"] is False
    assert record["focus_open_state_after"] == "open"
    assert world_for(PACKAGE, state.facts).axis_values("michelle_drawer").get("open") == "open"


def test_open_step_is_inert_when_the_container_is_not_openable(monkeypatch: pytest.MonkeyPatch) -> None:
    state, provider, record = _synthetic_capture(monkeypatch, openable=False, open=False)
    world = world_for(state.package, state.facts)

    assert record["engine_opened"] is False
    assert world.axis_values("tray").get("open") is None
    assert provider.observation_request == ObservationRequest("Open the survey tray.", "open", "tray")


def test_open_step_is_inert_when_the_container_is_out_of_sight(monkeypatch: pytest.MonkeyPatch) -> None:
    state, provider, record = _synthetic_capture(monkeypatch, openable=True, open=False, hidden=True)
    world = world_for(state.package, state.facts)

    assert world.sees("hero", "tray") is False
    assert record["engine_opened"] is False
    assert record["focus_open_state_after"] is None
    assert world.axis_values("tray").get("open") == "closed"
    assert provider.observation_request is None


def test_open_step_rolls_back_when_enforcement_rejects_both_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_at("kitchen")
    provider = _ScriptedProvider(
        state,
        [("Nothing is shown.", None), ("Still nothing is shown.", None)],
    )
    before = copy.deepcopy(state.snapshot())
    asks: list[object] = []

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        asks.append(questions)
        return {key: {"noul": 1.0 if key == "opens_container" else 0.0} for key in questions}

    capture = WorldCapture(provider, ask)
    capture.enforcing_verifier = ObservationVerifier(ask)
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["drawer"], "same_as": {}},
    )

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, provider, capture=capture).turn("Open the drawer.")

    assert caught.value.code == "observation_unverified"
    after_world = world_for(PACKAGE, state.facts)
    before_world = world_for(PACKAGE, before.facts)
    assert after_world.axis_values("michelle_drawer").get("open") == "closed"
    assert {entity_id: after_world.parent(entity_id) for entity_id in after_world.entity_ids()} == {
        entity_id: before_world.parent(entity_id) for entity_id in before_world.entity_ids()
    }
    assert len(asks) >= 2


def test_open_step_works_for_a_second_synthetic_story(monkeypatch: pytest.MonkeyPatch) -> None:
    state, provider, record = _synthetic_capture(monkeypatch, openable=True, open=False)
    world = world_for(state.package, state.facts)

    assert record["engine_opened"] is True
    assert record["focus_open_state_after"] == "open"
    assert world.axis_values("tray").get("open") == "open"
    context = build_observation_context(
        world,
        "hero",
        ObservationRequest("Open the survey tray.", "open", "tray"),
    )
    assert context.action == "Open the survey tray."
