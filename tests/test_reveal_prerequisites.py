from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package import StoryPackageError, load_story_package

PACKAGE = Path("data/stories/continuity-initiative")


def copied_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE, destination)
    return destination


def update_knowledge(root: Path, knowledge_id: str, requires: list[dict[str, object]]) -> None:
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text(encoding="utf-8"))
    item = next(item for item in catalog["knowledge"] if item["id"] == knowledge_id)
    item["requires"] = requires
    source.write_text(yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True), encoding="utf-8")


def test_continuity_package_loads() -> None:
    package = load_story_package(PACKAGE)

    assert package.story_id == "continuity_initiative"


def test_loader_rejects_required_reveal_with_unproducible_scene_prerequisite(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text(encoding="utf-8"))
    item = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_2c_c_r1")
    item["requires"].append({"fact_id": "michelle_resistance_known", "equals": True})
    source.write_text(yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True), encoding="utf-8")

    with pytest.raises(
        StoryPackageError,
        match=re.escape(
            "scene 2C reveal 'k_sl_2c_c_r1' requires 'michelle_resistance_known', which scene entry does not "
            "guarantee and the scene cannot produce"
        ),
    ):
        load_story_package(root)
