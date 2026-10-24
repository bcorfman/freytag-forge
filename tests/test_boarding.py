from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from worldkeeper import MemoryBackend, World, WorldSchema

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


def test_approaching_vehicle_does_not_board():
    _, world = _at_truck()

    asked = []

    def answer(command, vehicle):
        asked.append((command, vehicle))
        return False

    result = board_vehicle(world, PACKAGE, "Go out to Kristin's truck.", answer)

    assert result.steps == ()
    assert result.asked is True
    assert asked == [("Go out to Kristin's truck.", "Kristin's truck")]
    assert world.parent("kristin") == "outside_house"


def test_boards_vehicle_and_notices_visible_laptop():
    _, world = _at_truck()

    result = board_vehicle(world, PACKAGE, "Get in Kristin's truck.", lambda *_: True)

    assert result.steps == (
        "Kristin sat down in the driver's seat.",
        "Kristin's laptop sat on the passenger seat.",
    )
    assert result.command == (
        "Kristin sat down in the driver's seat. Kristin's laptop sat on the passenger seat. Get in Kristin's truck."
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


def test_contextual_boarding_uses_the_only_vehicle_in_the_area():
    _, world = _at_truck()
    asked = []

    result = board_vehicle(world, PACKAGE, "Get in.", lambda *args: asked.append(args) or True)

    assert result.steps == (
        "Kristin sat down in the driver's seat.",
        "Kristin's laptop sat on the passenger seat.",
    )
    assert asked == [("Get in.", "Kristin's truck")]
    assert world.parent("kristin") == "truck_driver_seat"


def test_contextual_boarding_does_not_ask_inside_the_house():
    _, world = _world()
    initial_parent = world.parent("kristin")
    asked = []

    result = board_vehicle(world, PACKAGE, "Get in.", lambda *args: asked.append(args) or True)

    assert result.steps == ()
    assert result.asked is False
    assert asked == []
    assert world.parent("kristin") == initial_parent


def test_boarding_omits_a_carried_laptop_notice():
    _, world = _at_truck()
    assert world.move("kristin_laptop", "kristin").ok

    result = board_vehicle(world, PACKAGE, "Get in.", lambda *_: True)

    assert result.steps == ("Kristin sat down in the driver's seat.",)


def test_boarding_omits_a_laptop_left_in_the_house():
    _, world = _world()
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "mcgehee_home").ok

    result = board_vehicle(world, PACKAGE, "Get in.", lambda *_: True)

    assert result.steps == ("Kristin sat down in the driver's seat.",)


def test_already_aboard_is_not_asked():
    _, world = _at_truck()
    assert world.move("kristin", "truck_driver_seat").ok
    asked = []

    result = board_vehicle(world, PACKAGE, "Drive Kristin's truck.", lambda *args: asked.append(args) or True)

    assert result.steps == ()
    assert result.asked is False
    assert asked == []


def test_repeated_contextual_boarding_while_seated_is_not_asked():
    _, world = _at_truck()
    assert world.move("kristin", "truck_driver_seat").ok
    asked = []

    result = board_vehicle(world, PACKAGE, "Get in.", lambda *args: asked.append(args) or True)

    assert result.steps == ()
    assert result.asked is False
    assert asked == []


def _synthetic_vehicle_world(vehicle_count=1):
    entities = [
        {"id": "harbor", "name": "harbor", "kind": "area"},
        {"id": "player", "name": "Player", "kind": "character"},
    ]
    items = [
        SimpleNamespace(id="player", seat_for=None, enter_text=None, notice_text=None),
    ]
    for index in range(vehicle_count):
        vehicle_id = f"boat_{index}"
        seat_id = f"boat_seat_{index}"
        cargo_id = f"rope_{index}"
        entities.extend(
            [
                {"id": vehicle_id, "name": f"boat {index}", "kind": "boat"},
                {
                    "id": seat_id,
                    "name": f"boat seat {index}",
                    "kind": "seat",
                    "enterable": True,
                    "seat_for": vehicle_id,
                    "enter_pole": "occupied",
                    "axes": [{"poles": ["empty", "occupied"], "initial": "empty"}],
                },
                {"id": cargo_id, "name": f"rope {index}", "kind": "thing"},
            ]
        )
        items.extend(
            [
                SimpleNamespace(id=vehicle_id, seat_for=None, enter_text=None, notice_text=None),
                SimpleNamespace(
                    id=seat_id,
                    seat_for=vehicle_id,
                    enter_text="Player settled into the boat seat.",
                    notice_text=None,
                ),
                SimpleNamespace(
                    id=cargo_id,
                    seat_for=None,
                    enter_text=None,
                    notice_text="A coil of rope lay in the boat.",
                ),
            ]
        )
    schema = WorldSchema.from_data(
        {
            "kinds": [
                {"id": "boat", "is": ["vehicle"], "enterable": True},
                {"id": "seat", "is": ["supporter"], "enterable": True},
            ],
            "entities": entities,
        }
    )
    world = World(schema, MemoryBackend())
    world.seed()
    assert world.move("player", "harbor").ok
    for index in range(vehicle_count):
        vehicle_id = f"boat_{index}"
        assert world.move(vehicle_id, "harbor").ok
        assert world.move(f"boat_seat_{index}", vehicle_id).ok
        assert world.move(f"rope_{index}", vehicle_id).ok
    package = SimpleNamespace(protagonist_id="player", world=SimpleNamespace(items=tuple(items)))
    return package, world


def test_synthetic_vehicle_named_and_contextual_boarding_is_story_neutral():
    package, world = _synthetic_vehicle_world()
    named = []

    result = board_vehicle(world, package, "Get into the boat 0.", lambda _command, name: named.append(name) or True)

    assert result.steps == ("Player settled into the boat seat.", "A coil of rope lay in the boat.")
    assert named == ["boat 0"]

    package, world = _synthetic_vehicle_world()
    contextual = []
    result = board_vehicle(world, package, "Get in.", lambda _command, name: contextual.append(name) or True)

    assert result.steps == ("Player settled into the boat seat.", "A coil of rope lay in the boat.")
    assert contextual == ["boat 0"]


def test_synthetic_vehicle_context_is_ambiguous_with_two_vehicles():
    package, world = _synthetic_vehicle_world(vehicle_count=2)
    asked = []

    result = board_vehicle(world, package, "Get in.", lambda *args: asked.append(args) or True)

    assert result.steps == ()
    assert result.asked is False
    assert asked == []
    assert world.parent("player") == "harbor"


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
        return {key: {"noul": 1.0 if key == "boards_vehicle" else 0.0}}

    record = WorldCapture(provider, ask).before_turn("Get in Kristin's truck.")

    assert record["boarding_steps"] == [
        "Kristin sat down in the driver's seat.",
        "Kristin's laptop sat on the passenger seat.",
    ]
    assert record["boarding_asked"] is True
    assert record["command"].startswith("Kristin sat down in the driver's seat.")
    assert "boards_vehicle" in seen_questions
    assert world.parent("kristin") == "truck_driver_seat"
