import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package import StoryPackageError, load_story_package

ROOT = Path(__file__).parents[1]


def _changed_package(tmp_path, change):
    root = tmp_path / "story"
    shutil.copytree(ROOT / "data/stories/continuity-initiative", root)
    path = root / "world.yaml"
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return root


def test_package_rejects_unknown_seat_for(tmp_path):
    root = _changed_package(
        tmp_path,
        lambda data: next(item for item in data["items"] if item["id"] == "workstation_chair").update(
            seat_for="unknown"
        ),
    )
    with pytest.raises(StoryPackageError):
        load_story_package(root)


def test_package_rejects_enter_pole_outside_axes(tmp_path):
    root = _changed_package(
        tmp_path,
        lambda data: next(item for item in data["items"] if item["id"] == "workstation_chair").update(
            enter_pole="missing"
        ),
    )
    with pytest.raises(StoryPackageError):
        load_story_package(root)


def test_package_rejects_enterable_plain_thing(tmp_path):
    root = _changed_package(
        tmp_path,
        lambda data: next(item for item in data["items"] if item["id"] == "workstation_chair").update(
            kind="thing", enterable=True
        ),
    )
    with pytest.raises(StoryPackageError):
        load_story_package(root)
