from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.engine import EngineRefusalTurn, RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_place_scoped_feed import _synthetic_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _seated_continuity_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin_laptop", "truck_passenger_seat").ok
    assert world.move("kristin", "truck_driver_seat").ok
    return state


def _capture(
    state: RuntimeState,
    answers: dict[str, bool | None],
    *,
    engine_refusal: bool = True,
):
    provider = build_capture_provider(state)
    provider.observe_automatically = True
    requested: list[str] = []

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        requested.extend(key.split(":", 1)[0] for key in questions)
        return {
            key: {"noul": 1.0 if answers.get(key.split(":", 1)[0]) else 0.0}
            for key in questions
            if answers.get(key.split(":", 1)[0]) is not None
        }

    return provider, WorldCapture(provider, ask, fixed_refusal=True, engine_refusal=engine_refusal), requested


def test_already_aboard_reply_precedes_standing_and_narration() -> None:
    state = _seated_continuity_state()
    provider, capture, requested = _capture(
        state,
        {"boards_vehicle": True, "only_boards_vehicle": True, "needs_to_stand": True},
    )
    world = world_for(PACKAGE, state.facts)
    before = {
        "protagonist": world.parent("kristin"),
        "seat": world.parent("truck_driver_seat"),
        "vehicle": world.parent("kristin_truck"),
        "laptop": world.parent("kristin_laptop"),
    }

    record = capture.before_turn("Get in the truck.")

    assert record["engine_refusal"] == "You're already in Kristin's truck."
    assert record["boarding_asked"] is True
    assert record["boarding_command_consumed"] is False
    assert record["steps"] == []
    assert "needs_to_stand" not in requested
    assert "moves_thing" not in requested
    assert "uses_thing" not in requested
    assert world.parent("kristin") == before["protagonist"]
    assert world.parent("truck_driver_seat") == before["seat"]
    assert world.parent("kristin_truck") == before["vehicle"]
    assert world.parent("kristin_laptop") == before["laptop"]
    assert provider.observation_request is None


def test_already_aboard_real_engine_path_is_a_no_turn_refusal() -> None:
    state = _seated_continuity_state()
    provider, capture, _requested = _capture(
        state,
        {"boards_vehicle": True, "only_boards_vehicle": True, "needs_to_stand": True},
    )
    narrator_calls: list[str] = []

    def narrator(command: str) -> dict[str, object]:
        narrator_calls.append(command)
        raise AssertionError("already-aboard refusal called the narrator")

    engine = RuntimeEngine(state, narrator, capture=capture)
    before = state.snapshot()
    result = engine.turn("Get in the truck.")

    assert isinstance(result, EngineRefusalTurn)
    assert result.narration == "You're already in Kristin's truck."
    assert state.turn_index == before.turn_index
    assert state.facts == before.facts
    assert narrator_calls == []


def test_compound_boarding_is_not_consumed_and_reuses_prefetched_answers() -> None:
    state = _seated_continuity_state()
    provider, capture, requested = _capture(
        state,
        {"boards_vehicle": True, "only_boards_vehicle": False, "needs_to_stand": False},
    )

    record = capture.before_turn("Get in the truck and look for my laptop.")

    assert record["engine_refusal"] == ""
    assert record["boarding_command_consumed"] is False
    assert requested.count("boards_vehicle") == 1
    assert requested.count("only_boards_vehicle") == 1


def test_compound_boarding_rechecks_after_standing_changes_world() -> None:
    state = _seated_continuity_state()
    provider, capture, requested = _capture(
        state,
        {"boards_vehicle": True, "only_boards_vehicle": False, "needs_to_stand": True},
    )

    record = capture.before_turn("Get in the truck and look for my laptop.")

    assert record["engine_refusal"] == ""
    assert record["boarding_command_consumed"] is False
    assert record["boarding_steps"]
    assert world_for(PACKAGE, state.facts).parent("kristin") == "truck_driver_seat"
    assert requested.count("boards_vehicle") == 1


def test_explicit_exit_still_stands_the_protagonist_up() -> None:
    state = _seated_continuity_state()
    provider, capture, _requested = _capture(
        state,
        {"boards_vehicle": False, "needs_to_stand": True},
    )
    record = capture.before_turn("Get out of the truck.")

    assert record["engine_refusal"] == ""
    assert world_for(PACKAGE, state.facts).parent("kristin") == "outside_house"


def test_boarding_from_outside_still_seats_the_protagonist() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "outside_house").ok
    provider, capture, _requested = _capture(
        state,
        {"boards_vehicle": True, "only_boards_vehicle": True},
    )

    record = capture.before_turn("Get in the truck.")

    assert record["engine_refusal"] == ""
    assert record["boarding_command_consumed"] is True
    assert world_for(PACKAGE, state.facts).parent("kristin") == "truck_driver_seat"


def test_engine_refusal_off_keeps_the_legacy_seated_flow() -> None:
    state = _seated_continuity_state()
    provider, capture, requested = _capture(
        state,
        {"boards_vehicle": True, "only_boards_vehicle": True, "needs_to_stand": True},
        engine_refusal=False,
    )

    record = capture.before_turn("Get in the truck.")

    assert record["engine_refusal"] == ""
    assert record["standing_steps"]
    assert "needs_to_stand" in requested


def test_synthetic_vehicle_uses_its_own_name_in_engine_reply() -> None:
    package = _synthetic_package()
    items = tuple(
        item.model_copy(update={"name": "canoe"})
        if item.id == "car"
        else item.model_copy(update={"name": "bow seat"})
        if item.id == "driver_seat"
        else item
        for item in package.world.items
    )
    package = package.model_copy(update={"world": package.world.model_copy(update={"items": items})})
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    assert world.move("hero", "driver_seat").ok
    provider = build_capture_provider(state)

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        return {key: {"noul": 1.0} for key in questions if key in {"boards_vehicle", "only_boards_vehicle"}}

    record = WorldCapture(provider, ask, engine_refusal=True).before_turn("Get in the canoe.")

    assert record["engine_refusal"] == "You're already in the canoe."
    assert world.parent("hero") == "driver_seat"
