from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.seating import board_vehicle
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_boarding import _synthetic_vehicle_world
from tests.test_place_scoped_feed import _synthetic_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _seated_truck():
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "truck_passenger_seat").ok
    assert world.move("kristin", "truck_driver_seat").ok
    return state, world


@pytest.mark.parametrize("command", ("Get in.", "Get in the truck."))
def test_repeated_boarding_is_consumed_without_repeating_entry(command: str) -> None:
    _, world = _seated_truck()
    asked: list[tuple[str, str]] = []

    def boards(player_input: str, vehicle: str) -> bool:
        asked.append((player_input, vehicle))
        return True

    result = board_vehicle(world, PACKAGE, command, boards, lambda *_: True)

    assert result.command == "Kristin Schweitzer is already in the driver's seat."
    assert result.steps == ("Kristin Schweitzer is already in the driver's seat.",)
    assert result.command_consumed is True
    assert result.issues == ()
    assert asked == [(command, "Kristin's truck")]
    assert world.parent("kristin") == "truck_driver_seat"
    assert world.parent("kristin_laptop") == "truck_passenger_seat"


def test_repeated_boarding_with_another_action_is_not_consumed() -> None:
    _, world = _seated_truck()
    asked: list[str] = []

    result = board_vehicle(
        world,
        PACKAGE,
        "Drive the truck.",
        lambda _command, vehicle: asked.append(vehicle) or True,
        lambda *_: False,
    )

    assert result.steps == ()
    assert result.command_consumed is False
    assert result.issues == ()
    assert asked == ["Kristin's truck"]
    assert world.parent("kristin") == "truck_driver_seat"


def test_repeated_boarding_false_does_not_change_world() -> None:
    _, world = _seated_truck()
    asked: list[str] = []

    result = board_vehicle(
        world,
        PACKAGE,
        "Get in.",
        lambda _command, vehicle: asked.append(vehicle) or False,
        lambda *_: True,
    )

    assert result.steps == ()
    assert result.command_consumed is False
    assert result.issues == ()
    assert asked == ["Kristin's truck"]
    assert world.parent("kristin") == "truck_driver_seat"


def test_boarding_a_different_visible_vehicle_keeps_normal_path() -> None:
    package, world = _synthetic_vehicle_world(vehicle_count=2)
    assert world.move("player", "boat_seat_0").ok

    result = board_vehicle(
        world,
        package,
        "Get into boat 1.",
        lambda *_: True,
        lambda *_: True,
    )

    assert result.command_consumed is True
    assert result.steps == ("Player settled into the boat seat.", "A coil of rope lay in the boat.")
    assert world.parent("player") == "boat_seat_1"


def test_synthetic_story_uses_its_vehicle_name_for_repeated_boarding() -> None:
    package = _synthetic_package()
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    assert world.move("hero", "driver_seat").ok

    result = board_vehicle(world, package, "Get in a blue car.", lambda *_: True, lambda *_: True)

    assert result.command == "Ari is already in the driver seat."
    assert result.steps == ("Ari is already in the driver seat.",)
    assert result.command_consumed is True
    assert world.parent("hero") == "driver_seat"


def test_repeated_boarding_with_non_consuming_classifier_calls_narrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, _world = _seated_truck()
    provider = build_capture_provider(state)
    calls: list[object] = []

    def ask(command, questions):
        return {question: {"noul": 1.0 if question == "boards_vehicle" else 0.0} for question in questions}

    engine = RuntimeEngine(
        state,
        provider,
        capture=WorldCapture(provider, ask, fixed_refusal=True, engine_refusal=True),
    )

    def open_request(request, **_kwargs: object) -> _Response:
        calls.append(request)
        return _Response({"segments": [{"kind": "narration", "text": "The truck is quiet."}]})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    result = engine.turn("Get in.")

    assert result.narration.startswith("The truck is quiet.")
    assert calls
    assert provider.last_turn_engine_text is False
    assert world_for(PACKAGE, state.facts).parent("kristin") == "truck_driver_seat"


def test_boarding_sequence_uses_engine_text_for_both_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "truck_passenger_seat").ok
    provider = build_capture_provider(state)
    calls: list[object] = []

    def ask(command, questions):
        return {
            question: {
                "noul": 1.0
                if question in {"boards_vehicle", "only_boards_vehicle"}
                and command["command"] in {"Go to the truck.", "Get in."}
                else 0.0
            }
            for question in questions
        }

    engine = RuntimeEngine(
        state,
        provider,
        capture=WorldCapture(provider, ask, fixed_refusal=True, engine_refusal=True),
    )
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda request, **_kwargs: (
            calls.append(request) or pytest.fail("the consumed boarding sequence called the narrator")
        ),
    )

    first = engine.turn("Go to the truck.")
    second = engine.turn("Get in.")

    assert first.narration != second.narration
    assert first.narration.startswith(
        "Kristin sat down in the driver's seat. Kristin's laptop sat on the passenger seat."
    )
    assert second.narration == "Kristin Schweitzer is already in the driver's seat."
    assert world.parent("kristin") == "truck_driver_seat"
    assert world.parent("kristin_laptop") == "truck_passenger_seat"
    assert calls == []
    print(f"test (a) final narration: {second.narration}")
    print(f"test (g) first narration: {first.narration}")
    print(f"test (g) second narration: {second.narration}")
