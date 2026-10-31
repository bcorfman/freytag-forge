from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_package.world_schema import world_source_schema_data

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
PACKAGE = load_story_package(PACKAGE_ROOT)
EXPECTED_SCHEMA_HASH = "eb5ad8c111719bf5da53495974a4e1ab3a41806b538b99a72586c9b42418858d"


def _schema_hash(package, schema_data=None) -> str:
    if schema_data is None:
        schema_data = world_source_schema_data(package.world)
    payload = json.dumps(schema_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _copy_package(tmp_path: Path) -> tuple[Path, dict]:
    root = tmp_path / "story"
    shutil.copytree(PACKAGE_ROOT, root)
    world_path = root / "world.yaml"
    world = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    return root, world


def _write_world(root: Path, world: dict) -> None:
    (root / "world.yaml").write_text(yaml.safe_dump(world, sort_keys=False), encoding="utf-8")


def test_unmodified_package_schema_is_byte_identical(tmp_path):
    root, world = _copy_package(tmp_path)

    copied = load_story_package(root)

    schema_data = world_source_schema_data(PACKAGE.world)
    passenger_seat = next(entity for entity in schema_data["entities"] if entity["id"] == "truck_passenger_seat")
    assert passenger_seat["contents_complete"] is True
    assert all(
        entity["id"] == "truck_passenger_seat" or not {"contents_complete", "view"} & entity.keys()
        for entity in schema_data["entities"]
    )

    schema_without_contents_complete = deepcopy(schema_data)
    passenger_seat = next(
        entity for entity in schema_without_contents_complete["entities"] if entity["id"] == "truck_passenger_seat"
    )
    del passenger_seat["contents_complete"]

    assert _schema_hash(PACKAGE, schema_without_contents_complete) == EXPECTED_SCHEMA_HASH
    assert _schema_hash(copied) == _schema_hash(PACKAGE)


def test_item_view_is_passed_through_to_worldkeeper(tmp_path):
    root, world = _copy_package(tmp_path)
    vehicle = next(item for item in world["items"] if item["id"] == "kristin_truck")
    vehicle["view"] = [{"from": "outside_house", "blocked_by": {"axis": "kristin_laptop", "pole": "open"}}]
    _write_world(root, world)

    package = load_story_package(root)
    state = RuntimeState.bootstrap(package)
    loaded_world = world_for(package, state.facts)
    assert loaded_world.move("kristin", "outside_house").ok
    assert loaded_world.move("kristin_laptop", "kristin_truck").ok

    shipped_state = RuntimeState.bootstrap(PACKAGE)
    shipped_world = world_for(PACKAGE, shipped_state.facts)
    assert shipped_world.move("kristin", "outside_house").ok
    assert shipped_world.move("kristin_laptop", "kristin_truck").ok

    assert loaded_world.sees("kristin", "kristin_laptop") is True
    assert shipped_world.sees("kristin", "kristin_laptop") is False


def test_contents_complete_is_passed_through_to_worldkeeper(tmp_path):
    root, world = _copy_package(tmp_path)
    drawer = next(item for item in world["items"] if item["id"] == "michelle_drawer")
    drawer["contents_complete"] = True
    _write_world(root, world)

    package = load_story_package(root)
    state = RuntimeState.bootstrap(package)
    loaded_world = world_for(package, state.facts)
    shipped_state = RuntimeState.bootstrap(PACKAGE)
    shipped_world = world_for(PACKAGE, shipped_state.facts)

    assert loaded_world.contents_complete("michelle_drawer") is True
    assert shipped_world.contents_complete("michelle_drawer") is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("from", "unknown_entity"),
        ("blocked_by", {"axis": "unknown_axis", "pole": "open"}),
        ("blocked_by", {"axis": "kristin_laptop", "pole": "unknown_pole"}),
    ],
)
def test_invalid_item_view_declarations_are_story_package_errors(tmp_path, field, value):
    root, world = _copy_package(tmp_path)
    vehicle = next(item for item in world["items"] if item["id"] == "kristin_truck")
    view = {"from": "outside_house"}
    view[field] = value
    vehicle["view"] = [view]
    _write_world(root, world)

    with pytest.raises(StoryPackageError):
        load_story_package(root)


@pytest.mark.parametrize("value", ([True], "yes", 1))
def test_non_boolean_contents_complete_is_story_package_error(tmp_path, value):
    root, world = _copy_package(tmp_path)
    drawer = next(item for item in world["items"] if item["id"] == "michelle_drawer")
    drawer["contents_complete"] = value
    _write_world(root, world)

    with pytest.raises(StoryPackageError):
        load_story_package(root)
