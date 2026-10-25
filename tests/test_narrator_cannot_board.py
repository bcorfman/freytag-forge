from pathlib import Path

import pytest

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
BOARDING_ISSUE = (
    "item_facts for 'Kristin' placed her in the vehicle \"Kristin's truck\" but the command did not board it; "
    "kept at the vehicle's area"
)


def _seeded_provider() -> ItemFactsProvider:
    return ItemFactsProvider(
        worker_url="",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
        item_facts={},
        mode="off",
        seed_from_package=True,
    )


def test_unboarded_protagonist_stays_outside_and_laptop_moves_to_passenger_seat():
    provider = _seeded_provider()
    world = provider._world()
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "outside_house").ok

    _facts, issues = provider.apply_item_facts(
        {
            "Kristin": {"place": "Kristin's truck"},
            "Kristin's laptop": {"place": "passenger seat"},
        },
        player_input="Walk over to the truck and look through the window.",
    )

    assert world.parent("kristin") == "outside_house"
    assert world.parent("kristin") != "truck_driver_seat"
    assert world.parent("kristin_laptop") == "truck_passenger_seat"
    assert issues == [BOARDING_ISSUE]


def test_unboarded_protagonist_in_a_room_moves_to_the_vehicle_area():
    provider = _seeded_provider()
    world = provider._world()
    assert world.move("kristin", "kitchen").ok

    _facts, issues = provider.apply_item_facts(
        {"Kristin": {"place": "Kristin's truck"}},
        player_input="Walk over to the truck.",
    )

    assert world.parent("kristin") == "outside_house"
    assert world.parent("kristin") != "truck_driver_seat"
    assert issues == [BOARDING_ISSUE]


def test_unboarded_protagonist_cannot_board_from_a_direct_seat_report():
    provider = _seeded_provider()
    world = provider._world()
    assert world.move("kristin", "outside_house").ok

    _facts, issues = provider.apply_item_facts(
        {"Kristin": {"place": "driver's seat"}},
        player_input="Look through the truck window.",
    )

    assert world.parent("kristin") == "outside_house"
    assert world.parent("kristin") != "truck_driver_seat"
    assert issues == [BOARDING_ISSUE]


@pytest.mark.parametrize("reported_place", ("Kristin's truck", "driver's seat"))
def test_already_boarded_protagonist_keeps_engine_boarding(reported_place: str):
    provider = _seeded_provider()
    world = provider._world()
    assert world.move("kristin", "truck_driver_seat").ok

    _facts, issues = provider.apply_item_facts(
        {"Kristin": {"place": reported_place}},
        player_input="Look around the truck.",
    )

    assert world.parent("kristin") == "truck_driver_seat"
    assert issues == []


def test_non_protagonist_can_still_move_into_a_vehicle():
    provider = _seeded_provider()
    world = provider._world()
    assert world.move("michelle", "outside_house").ok

    _facts, issues = provider.apply_item_facts(
        {"Michelle": {"place": "Kristin's truck"}},
        player_input="Move Michelle to the truck.",
    )

    assert world.parent("michelle") == "kristin_truck"
    assert issues == []
