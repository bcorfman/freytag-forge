from __future__ import annotations

from pathlib import Path

from storygame.runtime.capture import WorldCapture
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.seating import board_vehicle
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _world():
    state = RuntimeState.bootstrap(PACKAGE)
    return state, world_for(PACKAGE, state.facts)


def _at_truck():
    state, world = _world()
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "truck_passenger_seat").ok
    return state, world


def test_boards_vehicle_and_notices_visible_laptop():
    _, world = _at_truck()

    result = board_vehicle(world, PACKAGE, "Go out to Kristin's truck.", lambda *_: True)

    assert result.steps == (
        "Kristin sat down in the driver's seat.",
        "Kristin's laptop sat on the passenger seat.",
    )
    assert result.command == (
        "Kristin sat down in the driver's seat. Kristin's laptop sat on the passenger seat. Go out to Kristin's truck."
    )
    assert world.parent("kristin") == "truck_driver_seat"


def test_boarding_false_does_not_move():
    _, world = _at_truck()

    result = board_vehicle(world, PACKAGE, "Look at Kristin's truck.", lambda *_: False)

    assert result.steps == ()
    assert result.asked is True
    assert world.parent("kristin") == "outside_house"


def test_boarding_unanswered_records_issue_without_moving():
    _, world = _at_truck()

    result = board_vehicle(world, PACKAGE, "Go out to Kristin's truck.", lambda *_: None)

    assert result.steps == ()
    assert result.issues == ("boarding question unanswered for 'Kristin's truck'",)
    assert world.parent("kristin") == "outside_house"


def test_boarding_does_not_ask_when_command_does_not_name_vehicle():
    _, world = _at_truck()
    asked = []

    result = board_vehicle(world, PACKAGE, "Wait outside the house.", lambda *args: asked.append(args) or True)

    assert result.steps == ()
    assert result.asked is False
    assert asked == []


def test_already_aboard_is_not_asked():
    _, world = _at_truck()
    assert world.move("kristin", "truck_driver_seat").ok
    asked = []

    result = board_vehicle(world, PACKAGE, "Drive Kristin's truck.", lambda *args: asked.append(args) or True)

    assert result.steps == ()
    assert result.asked is False
    assert asked == []


def test_capture_records_boarding_steps_and_prefix():
    state, world = _at_truck()
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="off",
        seed_from_package=True,
        held_by=True,
    )
    seen_questions = []

    def ask(_state, questions):
        key = next(iter(questions))
        seen_questions.append(key)
        return {key: {"noul": 1.0 if key == "goes_to_vehicle" else 0.0}}

    record = WorldCapture(provider, ask).before_turn("Go out to Kristin's truck.")

    assert record["boarding_steps"] == [
        "Kristin sat down in the driver's seat.",
        "Kristin's laptop sat on the passenger seat.",
    ]
    assert record["boarding_asked"] is True
    assert record["command"].startswith("Kristin sat down in the driver's seat.")
    assert "goes_to_vehicle" in seen_questions
    assert world.parent("kristin") == "truck_driver_seat"
