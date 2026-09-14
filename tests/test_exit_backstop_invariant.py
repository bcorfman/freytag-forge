from __future__ import annotations

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


def _edit_yaml(root: Path, filename: str, edit) -> None:
    source = root / filename
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    edit(document)
    source.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _add_world_fact(document: dict[str, object], fact_id: str) -> None:
    document["facts"].append(fact_id)  # type: ignore[union-attr]


def _add_knowledge_fact(document: dict[str, object], fact_id: str) -> None:
    document["facts"].append({"id": fact_id, "purpose": "A synthetic invariant test fact."})  # type: ignore[union-attr]


def _add_route_fact(document: dict[str, object], fact_id: str) -> None:
    document["new_fact_ids"].append(  # type: ignore[union-attr]
        {
            "id": fact_id,
            "definition": "A synthetic invariant test fact.",
            "used_by_storylets": [],
            "used_by_transitions": [],
        }
    )


def test_loader_rejects_missing_bridge_delivery_with_scene_and_fact(tmp_path: Path) -> None:
    root = copied_package(tmp_path)

    def remove_delivery(document: dict[str, object]) -> None:
        document["deliveries"] = [
            delivery
            for delivery in document["deliveries"]  # type: ignore[union-attr]
            if delivery["fact_id"] != "park_pursuit_resolved"  # type: ignore[index]
        ]

    _edit_yaml(root, "handoffs.yaml", remove_delivery)

    with pytest.raises(
        StoryPackageError,
        match="scene 1B bridge-required fact 'park_pursuit_resolved' has no FactDelivery",
    ):
        load_story_package(root)


def test_loader_rejects_transition_trigger_without_source_scene_producer(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    fact_id = "unbacked_trigger_fact"
    _edit_yaml(root, "world.yaml", lambda document: _add_world_fact(document, fact_id))
    _edit_yaml(root, "knowledge.yaml", lambda document: _add_knowledge_fact(document, fact_id))
    _edit_yaml(root, "storylet-routes.yaml", lambda document: _add_route_fact(document, fact_id))

    def replace_trigger(document: dict[str, object]) -> None:
        transition = next(item for item in document["transitions"] if item["id"] == "t_1c_2a")  # type: ignore[union-attr]
        transition["triggers"] = [{"fact_id": fact_id, "equals": True}]  # type: ignore[index]

    _edit_yaml(root, "pacing.yaml", replace_trigger)

    with pytest.raises(
        StoryPackageError,
        match=(
            "scene 1C transition 't_1c_2a' trigger 'unbacked_trigger_fact' "
            "is not asserted by a bridge event, pacing event or delivery cost"
        ),
    ):
        load_story_package(root)


def test_loader_rejects_bridge_activation_without_delivery_or_world_action(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    fact_id = "unbacked_bridge_fact"
    _edit_yaml(root, "world.yaml", lambda document: _add_world_fact(document, fact_id))
    _edit_yaml(root, "knowledge.yaml", lambda document: _add_knowledge_fact(document, fact_id))

    def add_activation_fact(document: dict[str, object]) -> None:
        event = next(
            item
            for item in document["canonical_bridge_events"]  # type: ignore[union-attr]
            if item["id"] == "bridge_1c_infiltration_needed"
        )
        event["activation"]["all_facts_true"].append(fact_id)  # type: ignore[index]

    _edit_yaml(root, "storylet-routes.yaml", add_activation_fact)

    with pytest.raises(
        StoryPackageError,
        match="scene 1C bridge-required fact 'unbacked_bridge_fact' has no FactDelivery",
    ):
        load_story_package(root)


def test_continuity_package_accepts_2a_world_only_bridge_fact_without_delivery() -> None:
    package = load_story_package(PACKAGE)

    assert any(
        event.scene_id == "2A" and "rebecca_observing_infiltrators" in event.activation.all_facts_true
        for event in package.storylet_routes.bridge_events
    )
    assert "rebecca_observing_infiltrators" not in {delivery.fact_id for delivery in package.deliveries}
