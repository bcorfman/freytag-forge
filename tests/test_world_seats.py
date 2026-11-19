import pytest

from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, patch_source


def _changed_package(tmp_path, address, value):
    root = compiled_story_copy(tmp_path)
    patch_source(root / "source", "catalog.yaml", address, value)
    return root


def test_package_rejects_unknown_seat_for(tmp_path):
    root = _changed_package(
        tmp_path,
        "items.workstation_chair.seat_for",
        "unknown",
    )
    with pytest.raises((StoryPackageError, SourceError)):
        load_story_package(root)


def test_package_rejects_enter_pole_outside_axes(tmp_path):
    root = _changed_package(
        tmp_path,
        "items.workstation_chair.enter_pole",
        "missing",
    )
    with pytest.raises((StoryPackageError, SourceError)):
        load_story_package(root)


def test_axis_unavailable_must_be_a_pole(tmp_path):
    root = _changed_package(
        tmp_path,
        "items.workstation_chair.unavailable",
        "gone",
    )
    with pytest.raises((StoryPackageError, SourceError), match="item 'workstation_chair' unavailable is not a pole"):
        load_story_package(root)


def test_npc_axis_unavailable_must_be_a_pole(tmp_path):
    root = _changed_package(
        tmp_path,
        "characters.brandon.unavailable",
        "gone",
    )
    with pytest.raises((StoryPackageError, SourceError), match="npc 'brandon' unavailable is not a pole"):
        load_story_package(root)


def test_package_rejects_enterable_plain_thing(tmp_path):
    root = _changed_package(
        tmp_path,
        "items.workstation_chair.kind",
        "thing",
    )
    patch_source(root / "source", "catalog.yaml", "items.workstation_chair.enterable", True)
    with pytest.raises((StoryPackageError, SourceError)):
        load_story_package(root)
