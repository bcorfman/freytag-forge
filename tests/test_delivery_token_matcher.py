from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_package.loader import _delivery_token_matcher

PACKAGE = Path("data/stories/continuity-initiative")


def _copy_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE, destination)
    return destination


def test_delivery_fact_id_is_rejected_as_an_implementation_only_token(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    knowledge_path = package_root / "knowledge.yaml"
    data = yaml.safe_load(knowledge_path.read_text(encoding="utf-8"))
    fact_id = "continuity_initiative_known"
    entry = next(item for item in data["knowledge"] if item.get("delivery_text"))
    entry["delivery_text"] += f" {fact_id}."
    knowledge_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match=rf"implementation-only token '{fact_id}'"):
        load_story_package(package_root)


def test_unmodified_package_loads() -> None:
    assert load_story_package(PACKAGE)


def test_delivery_token_matcher_respects_token_boundaries() -> None:
    package = load_story_package(PACKAGE)
    fact_id = "continuity_initiative_known"
    matcher = _delivery_token_matcher(package)

    assert matcher.search(f"x{fact_id}".casefold()) is None
    assert matcher.search(f"{fact_id}-y".casefold()) is None
    assert matcher.search(f"See {fact_id}.".casefold())
