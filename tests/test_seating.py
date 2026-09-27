from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.seating import seat_before_use, stand_before_leave
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package import StoryPackageError, load_story_package

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
PACKAGE = load_story_package(PACKAGE_ROOT)


def _world():
    state = RuntimeState.bootstrap(PACKAGE)
    return state, world_for(PACKAGE, state.facts)


def _put_player_and_laptop_in_kitchen(world):
    assert world.move("kristin", "kitchen").ok
    assert world.move("kristin_laptop", "kitchen").ok


def test_overturned_chair_is_righted_then_kristin_sits():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == (
        "Kristin set the workstation chair upright.",
        "Kristin sat down in the workstation chair.",
        "Kristin picked up her laptop.",
    )
    assert result.command == (
        "Kristin set the workstation chair upright. Kristin sat down in the workstation chair. "
        "Kristin picked up her laptop. "
        "Read the files on my laptop."
    )
    assert "upright" in world.axis_values("workstation_chair").values()
    assert world.parent("kristin") == "workstation_chair"


def test_upright_chair_only_seats_kristin():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    world.set_axis("workstation_chair", "upright")

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == (
        "Kristin sat down in the workstation chair.",
        "Kristin picked up her laptop.",
    )
    assert world.parent("kristin") == "workstation_chair"


def test_laptop_on_chosen_seat_is_picked_up():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin_laptop", "workstation_chair").ok
    world.set_axis("workstation_chair", "upright")

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == (
        "Kristin sat down in the workstation chair.",
        "Kristin picked up her laptop.",
    )
    assert world.holder("kristin_laptop") == "kristin"


def test_laptop_on_a_seat_for_another_furniture_is_picked_up():
    _, world = _world()
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "truck_driver_seat").ok

    result = seat_before_use(
        world,
        PACKAGE,
        "Read the files on Michelle's memory card with my laptop.",
        lambda *_: True,
    )

    assert result.steps == (
        "Kristin sat down in the driver's seat.",
        "Kristin picked up her laptop.",
    )
    assert world.holder("kristin_laptop") == "kristin"


def test_seated_kristin_gets_no_steps():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin_laptop", "michelle_workstation").ok
    assert world.move("kristin", "workstation_chair").ok

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == ()
    assert result.asked is True


def test_already_seated_picks_up_thing_loose_in_vehicle():
    _, world = _world()
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "kristin_truck").ok
    assert world.move("kristin", "truck_driver_seat").ok

    result = seat_before_use(
        world,
        PACKAGE,
        "Read the files on Michelle's memory card with my laptop.",
        lambda *_: True,
    )

    assert result.steps == ("Kristin picked up her laptop.",)
    assert world.holder("kristin_laptop") == "kristin"
    assert world.parent("kristin") == "truck_driver_seat"


def test_already_seated_at_desk_leaves_thing_on_desk():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin_laptop", "michelle_workstation").ok
    assert world.move("kristin", "workstation_chair").ok

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == ()
    assert world.parent("kristin_laptop") == "michelle_workstation"
    assert world.parent("kristin") == "workstation_chair"


def test_already_seated_holding_thing_needs_no_pickup():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin_laptop", "kristin").ok
    assert world.move("kristin", "workstation_chair").ok

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == ()
    assert world.holder("kristin_laptop") == "kristin"
    assert world.parent("kristin") == "workstation_chair"


def test_kristin_in_an_enterable_thing_gets_no_steps():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin", "workstation_chair").ok

    result = seat_before_use(world, PACKAGE, "Look at the workstation chair.", lambda *_: False)

    assert result.steps == ()
    assert result.command == "Look at the workstation chair."


def test_no_seat_nearby_gets_no_steps():
    _, world = _world()
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "kitchen").ok

    result = seat_before_use(world, PACKAGE, "Inspect Michelle's phone.", lambda *_: True)

    assert result.steps == ()
    assert result.asked is False


def test_truck_laptop_uses_driver_seat_and_is_picked_up():
    _, world = _world()
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "kristin_truck").ok

    result = seat_before_use(
        world,
        PACKAGE,
        "Read the files on Michelle's memory card with my laptop.",
        lambda *_: True,
    )

    assert result.steps == (
        "Kristin sat down in the driver's seat.",
        "Kristin picked up her laptop.",
    )
    assert world.parent("kristin") == "truck_driver_seat"
    assert world.holder("kristin_laptop") == "kristin"


def test_laptop_on_workstation_is_not_picked_up():
    _, world = _world()
    assert world.move("kristin", "kitchen").ok
    assert world.move("kristin_laptop", "michelle_workstation").ok
    world.set_axis("workstation_chair", "upright")

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == ("Kristin sat down in the workstation chair.",)
    assert world.parent("kristin_laptop") == "michelle_workstation"


def test_a_no_answer_gets_no_steps():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    asked = []

    def unanswered(command, name):
        asked.append((command, name))
        return None

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", unanswered)

    assert result.steps == ()
    assert result.asked is True
    assert result.issues == ("seating question unanswered for 'Kristin's laptop'",)
    assert asked == [("Read the files on my laptop.", "Kristin's laptop")]


def test_question_is_not_asked_when_the_thing_is_elsewhere():
    _, world = _world()
    assert world.move("kristin", "kitchen").ok

    asked = []
    result = seat_before_use(
        world,
        PACKAGE,
        "Carry my laptop out to the truck.",
        lambda command, name: asked.append((command, name)) or True,
    )

    assert result.steps == ()
    assert result.asked is False
    assert asked == []


def test_loader_rejects_a_seat_without_its_lines(tmp_path):
    root = tmp_path / "story"
    shutil.copytree(PACKAGE_ROOT, root)
    path = root / "world.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    chair = next(item for item in data["items"] if item["id"] == "workstation_chair")
    chair.pop("enter_text")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="enter_text"):
        load_story_package(root)


def test_seated_kristin_stands_before_leaving():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin", "workstation_chair").ok
    asked = []

    def answer(command, seat_name, within_reach):
        asked.append((command, seat_name, within_reach))
        return True

    result = stand_before_leave(world, PACKAGE, "Go out to the truck.", answer)

    assert result.command == "Kristin stood up from the workstation chair. Go out to the truck."
    assert result.steps == ("Kristin stood up from the workstation chair.",)
    assert result.asked is True
    assert result.issues == ()
    assert world.parent("kristin") == "kitchen"
    assert asked == [("Go out to the truck.", "workstation chair", tuple(sorted(asked[0][2])))]


def test_seated_kristin_stays_on_a_no():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin", "workstation_chair").ok

    result = stand_before_leave(world, PACKAGE, "Read the files on my laptop.", lambda *_: False)

    assert result.command == "Read the files on my laptop."
    assert result.steps == ()
    assert result.asked is True
    assert world.parent("kristin") == "workstation_chair"


def test_standing_kristin_is_not_asked_to_stand():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    asked = []

    result = stand_before_leave(world, PACKAGE, "Go out to the truck.", lambda *args: asked.append(args) or True)

    assert result.steps == ()
    assert result.asked is False
    assert asked == []


def test_loader_rejects_a_seat_without_its_leave_line(tmp_path):
    root = tmp_path / "story"
    shutil.copytree(PACKAGE_ROOT, root)
    path = root / "world.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    chair = next(item for item in data["items"] if item["id"] == "workstation_chair")
    chair.pop("leave_text")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="leave_text"):
        load_story_package(root)
