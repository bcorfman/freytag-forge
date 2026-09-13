"""Classify storylets by the bridge facts they can establish."""

from __future__ import annotations

from storygame.story_package.models import StoryPackage


def required_storylet_ids(package: StoryPackage) -> frozenset[str]:
    """Return storylets that can establish a fact needed by a canonical route event."""

    bridge_facts_by_scene: dict[str, set[str]] = {}
    for bridge_event in package.storylet_routes.bridge_events:
        bridge_facts_by_scene.setdefault(bridge_event.scene_id, set()).update(bridge_event.activation.all_facts_true)
        bridge_facts_by_scene[bridge_event.scene_id].update(bridge_event.activation.any_of)

    route_storylet_ids = {
        storylet_id
        for event in package.storylet_routes.resolution_events
        for storylet_id in event.realization_storylets
    }

    return frozenset(
        storylet.id
        for storylet in package.storylet_routes.storylets
        if storylet.id in route_storylet_ids
        or any(
            operation.fact_id in bridge_facts_by_scene.get(storylet.scene_id, set())
            for realization in storylet.realizations
            for operation in realization.operations
        )
    )
