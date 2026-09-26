from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.seating import seat_before_use
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
        "Set the workstation chair upright.",
        "Sit in the workstation chair.",
    )
    assert result.command == (
        "Set the workstation chair upright. Sit in the workstation chair. Read the files on my laptop."
    )
    assert "upright" in world.axis_values("workstation_chair").values()
    assert world.parent("kristin") == "workstation_chair"


def test_upright_chair_only_seats_kristin():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    world.set_axis("workstation_chair", "upright")

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == ("Sit in the workstation chair.",)
    assert world.parent("kristin") == "workstation_chair"


def test_seated_kristin_gets_no_steps():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin", "workstation_chair").ok

    result = seat_before_use(world, PACKAGE, "Read the files on my laptop.", lambda *_: True)

    assert result.steps == ()
    assert result.asked is False


def test_kristin_in_an_enterable_thing_gets_no_steps():
    _, world = _world()
    _put_player_and_laptop_in_kitchen(world)
    assert world.move("kristin", "workstation_chair").ok

    result = seat_before_use(world, PACKAGE, "Look at the workstation chair.", lambda *_: True)

    assert result.steps == ()
    assert result.command == "Look at the workstation chair."


def test_no_seat_nearby_gets_no_steps():
    _, world = _world()
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "outside_house").ok

    result = seat_before_use(world, PACKAGE, "Carry my laptop out to the truck.", lambda *_: True)

    assert result.steps == ()
    assert result.asked is False


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
