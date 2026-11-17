from __future__ import annotations

from pathlib import Path

import pytest

from storygame.story_package import load_story_package
from storygame.story_source import compiler
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

PACKAGE = Path("data/stories/continuity-initiative")


def test_loader_rejects_missing_bridge_delivery_with_scene_and_fact(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(root, "source/scenes/1B.yaml", "facts.park_pursuit_resolved.delivery")

    with pytest.raises(
        SourceError,
        match="scene 1B bridge-required fact 'park_pursuit_resolved' has no FactDelivery",
    ):
        load_compiled_copy(root)


def test_loader_rejects_transition_trigger_without_source_scene_producer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = compiled_story_copy(tmp_path)
    fact_id = "unbacked_trigger_fact"
    patch_source(root, "source/scenes/1C.yaml", f"facts.{fact_id}", {"purpose": "A synthetic invariant test fact."})
    patch_source(root, "source/scenes/1C.yaml", "exit.when_all", [fact_id])
    monkeypatch.setattr(compiler, "_supply_transition_sources", lambda pacing, incidents, routes: pacing)

    with pytest.raises(
        SourceError,
        match=(
            "scene 1C transition 't_1c_2a' trigger 'unbacked_trigger_fact' "
            "is not asserted by a bridge event, pacing event or delivery cost"
        ),
    ):
        load_compiled_copy(root)


def test_loader_rejects_bridge_activation_without_delivery_or_world_action(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    fact_id = "unbacked_bridge_fact"
    patch_source(root, "source/scenes/1C.yaml", f"facts.{fact_id}", {"purpose": "A synthetic invariant test fact."})
    patch_source(root, "source/scenes/1C.yaml", "bridge[bridge_1c_infiltration_needed].when", [fact_id])

    with pytest.raises(
        SourceError,
        match="scene 1C bridge-required fact 'unbacked_bridge_fact' has no FactDelivery",
    ):
        load_compiled_copy(root)


def test_continuity_package_accepts_2a_world_only_bridge_fact_without_delivery() -> None:
    package = load_story_package(PACKAGE)

    assert any(
        event.scene_id == "2A" and "rebecca_observing_infiltrators" in event.activation.all_facts_true
        for event in package.storylet_routes.bridge_events
    )
    assert "rebecca_observing_infiltrators" in {delivery.fact_id for delivery in package.deliveries}
