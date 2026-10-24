from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package import StoryPackageError, load_story_package

FIXTURE = Path(__file__).parent / "fixtures" / "stories" / "lighthouse-incident"


def _package(tmp_path: Path, *, producer_scene: str = "1A", consumer: str = "k_copy_chart") -> Path:
    package = tmp_path / "lighthouse-incident"
    shutil.copytree(FIXTURE, package)

    incidents_path = package / "incidents.yaml"
    incidents = yaml.safe_load(incidents_path.read_text(encoding="utf-8"))
    incidents["incidents"] = []
    incidents_path.write_text(yaml.safe_dump(incidents, sort_keys=False), encoding="utf-8")

    pacing_path = package / "pacing.yaml"
    pacing = yaml.safe_load(pacing_path.read_text(encoding="utf-8"))
    pacing["transitions"] = []
    pacing_path.write_text(yaml.safe_dump(pacing, sort_keys=False), encoding="utf-8")

    plot_path = package / "plot.md"
    plot = plot_path.read_text(encoding="utf-8").replace(
        "transition_ids: [t_1a_1b]\nbridge_text:\n  t_1a_1b: Ada carries the lantern into the lamp room.",
        "transition_ids: []",
    )
    plot_path.write_text(plot, encoding="utf-8")

    knowledge_path = package / "knowledge.yaml"
    knowledge = yaml.safe_load(knowledge_path.read_text(encoding="utf-8"))
    knowledge["facts"].extend(
        [
            {"id": "pacing_produced", "purpose": "A pacing event produced this fact."},
            {"id": "never_produced", "purpose": "No package element produces this fact."},
        ]
    )
    item = next(entry for entry in knowledge["knowledge"] if entry["id"] == consumer)
    item["requires"] = [{"fact_id": "pacing_produced", "equals": True}]
    knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")

    world_path = package / "world.yaml"
    world = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    world["facts"].extend(["pacing_produced", "never_produced"])
    world_path.write_text(yaml.safe_dump(world, sort_keys=False), encoding="utf-8")

    pacing = yaml.safe_load(pacing_path.read_text(encoding="utf-8"))
    event = pacing["events"][0]
    event["scene_id"] = producer_scene
    event["at_turn"] = 0 if producer_scene == "1B" else 2
    event["effects"] = [{"fact_id": "pacing_produced", "equals": True}]
    pacing_path.write_text(yaml.safe_dump(pacing, sort_keys=False), encoding="utf-8")
    return package


def test_same_scene_pacing_effect_produces_required_fact(tmp_path: Path) -> None:
    load_story_package(_package(tmp_path))


def test_later_scene_can_require_fact_produced_by_pacing_event(tmp_path: Path) -> None:
    load_story_package(_package(tmp_path, consumer="k_lamp_room"))


def test_earlier_scene_cannot_require_fact_produced_by_later_pacing_event(tmp_path: Path) -> None:
    with pytest.raises(StoryPackageError, match="has an unreachable prerequisite"):
        load_story_package(_package(tmp_path, producer_scene="1B"))


def test_unproduced_required_fact_is_still_rejected(tmp_path: Path) -> None:
    package = _package(tmp_path)
    knowledge_path = package / "knowledge.yaml"
    knowledge = yaml.safe_load(knowledge_path.read_text(encoding="utf-8"))
    knowledge["knowledge"][0]["requires"] = [{"fact_id": "never_produced", "equals": True}]
    knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="has an unreachable prerequisite"):
        load_story_package(package)
