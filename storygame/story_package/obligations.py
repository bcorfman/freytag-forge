"""Classify storylets by the bridge facts they can establish."""

from __future__ import annotations

from storygame.story_package.models import StoryPackage


def required_storylet_ids(package: StoryPackage) -> frozenset[str]:
    """Return storylets whose operations can establish a fact needed by their scene bridge."""

    bridge_facts_by_scene: dict[str, set[str]] = {}
    for bridge_event in package.storylet_routes.bridge_events:
        bridge_facts_by_scene.setdefault(bridge_event.scene_id, set()).update(bridge_event.activation.all_facts_true)
        bridge_facts_by_scene[bridge_event.scene_id].update(bridge_event.activation.any_of)

    return frozenset(
        storylet.id
        for storylet in package.storylet_routes.storylets
        if any(
            operation.fact_id in bridge_facts_by_scene.get(storylet.scene_id, set())
            for realization in storylet.realizations
            for operation in realization.operations
        )
    )
