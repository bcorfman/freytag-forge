from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.traversal import match_traversal_command
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
HOUSE_ARRIVAL = "Kristin steps outside. Her truck is parked at the curb."
OUTSIDE_ARRIVAL = "Kristin goes back inside through the forced back door."


def provider_must_not_be_called(_command: str) -> dict[str, object]:
    raise AssertionError("traversal turns must not call the narrator provider")


def _state_at(place_id: str = "mcgehee_home") -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    assert world_for(PACKAGE, state.facts).move("kristin", place_id).ok
    return state


@pytest.mark.parametrize("place_id", ["mcgehee_home", "kitchen"])
@pytest.mark.parametrize("command", ["Go outside.", "Walk outside."])
def test_house_to_outside_is_engine_owned(place_id: str, command: str) -> None:
    state = _state_at(place_id)

    result = RuntimeEngine(state, provider_must_not_be_called).turn(command)

    assert result.narration == HOUSE_ARRIVAL
    assert world_for(PACKAGE, state.facts).parent("kristin") == "outside_house"


@pytest.mark.parametrize("command", ["Go inside.", "Go back inside."])
def test_outside_to_house_is_engine_owned(command: str) -> None:
    state = _state_at("outside_house")

    result = RuntimeEngine(state, provider_must_not_be_called).turn(command)

    assert result.narration == OUTSIDE_ARRIVAL
    assert world_for(PACKAGE, state.facts).parent("kristin") == "mcgehee_home"


def test_traversal_from_truck_seat_moves_kristin_to_house() -> None:
    state = _state_at("truck_driver_seat")
    world = world_for(PACKAGE, state.facts)
    assert world.parent("kristin") == "truck_driver_seat"

    result = RuntimeEngine(state, provider_must_not_be_called).turn("Go inside.")

    assert result.narration == OUTSIDE_ARRIVAL
    assert world.parent("kristin") == "mcgehee_home"
    assert world.parent("kristin") != "truck_driver_seat"


@pytest.mark.parametrize("command", ["Go out to the truck.", "Get in the truck.", "Look around."])
@pytest.mark.parametrize("place_id", ["mcgehee_home", "outside_house"])
def test_truck_and_observation_commands_are_not_traversals(place_id: str, command: str) -> None:
    state = _state_at(place_id)
    world = world_for(PACKAGE, state.facts)

    assert match_traversal_command(PACKAGE, state.facts, world, command) is None


def test_entering_house_while_inside_is_not_a_traversal() -> None:
    state = _state_at()
    world = world_for(PACKAGE, state.facts)

    assert match_traversal_command(PACKAGE, state.facts, world, "Go in the house.") is None


def test_location_aliases_resolve() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)

    assert world.resolve("the yard") == "outside_house"
    assert world.resolve("driveway") == "outside_house"
    assert world.resolve("outside") == "outside_house"
    assert world.resolve("inside") == "mcgehee_home"
    assert world.resolve("the living room") == "mcgehee_home"
    assert world.resolve("the front room") == "mcgehee_home"
    assert world.resolve("the hallway") == "mcgehee_home"


def test_scene_entry_bootstraps_kristin_in_the_house_and_connections_load() -> None:
    state = RuntimeState.bootstrap(PACKAGE)

    assert PACKAGE.connections is not None
    assert world_for(PACKAGE, state.facts).parent("kristin") == "mcgehee_home"
