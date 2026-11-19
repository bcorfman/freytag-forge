from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_package.world_schema import world_source_schema_data
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
PACKAGE = load_story_package(PACKAGE_ROOT)
EXPECTED_SCHEMA_HASH = "c377b2ad82b0eab3237ec8a04ede02d84ef8decc4264ff40ce93f1f1c1f7299d"


def _schema_hash(package, schema_data=None) -> str:
    if schema_data is None:
        schema_data = world_source_schema_data(package.world)
    payload = json.dumps(schema_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _copy_package(tmp_path: Path) -> Path:
    return compiled_story_copy(tmp_path)


def test_unmodified_package_schema_is_byte_identical(tmp_path):
    root = _copy_package(tmp_path)

    copied = load_compiled_copy(root)

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
    root = _copy_package(tmp_path)
    patch_source(
        root,
        "source/catalog.yaml",
        "items.kristin_truck.view",
        [{"from": "outside_house", "blocked_by": {"axis": "kristin_laptop", "pole": "open"}}],
    )

    package = load_compiled_copy(root)
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
    root = _copy_package(tmp_path)
    patch_source(root, "source/catalog.yaml", "items.michelle_drawer.contents_complete", True)

    package = load_compiled_copy(root)
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
    root = _copy_package(tmp_path)
    view = {"from": "outside_house"}
    view[field] = value
    patch_source(root, "source/catalog.yaml", "items.kristin_truck.view", [view])

    with pytest.raises((StoryPackageError, SourceError)):
        load_compiled_copy(root)


@pytest.mark.parametrize("value", ([True], "yes", 1))
def test_non_boolean_contents_complete_is_story_package_error(tmp_path, value):
    root = _copy_package(tmp_path)
    patch_source(root, "source/catalog.yaml", "items.michelle_drawer.contents_complete", value)

    with pytest.raises((StoryPackageError, SourceError)):
        load_compiled_copy(root)
