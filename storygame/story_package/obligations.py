"""Classify storylets by the bridge facts they can establish."""

from __future__ import annotations

from storygame.story_package.models import StoryPackage


def required_storylet_ids(package: StoryPackage) -> frozenset[str]:
    """Return storylets needed for canonical route events and their prerequisites."""

    bridge_facts_by_scene: dict[str, set[str]] = {}
    for bridge_event in package.storylet_routes.bridge_events:
        bridge_facts_by_scene.setdefault(bridge_event.scene_id, set()).update(bridge_event.activation.all_facts_true)
        bridge_facts_by_scene[bridge_event.scene_id].update(bridge_event.activation.any_of)

    route_storylet_ids = {
        storylet_id
        for event in package.storylet_routes.resolution_events
        for storylet_id in event.realization_storylets
    }

    required = {
        storylet.id
        for storylet in package.storylet_routes.storylets
        if storylet.id in route_storylet_ids
        or any(
            operation.fact_id in bridge_facts_by_scene.get(storylet.scene_id, set())
            for realization in storylet.realizations
            for operation in realization.operations
        )
    }

    storylets_by_id = {storylet.id: storylet for storylet in package.storylet_routes.storylets}
    knowledge_by_storylet: dict[str, list[object]] = {}
    for knowledge in package.knowledge_indexes.by_id.values():
        storylet_id = knowledge.source.storylet_id
        if storylet_id is not None:
            knowledge_by_storylet.setdefault(storylet_id, []).append(knowledge)

    changed = True
    while changed:
        changed = False
        needed_by_scene: dict[str, set[str]] = {}
        for storylet_id in required:
            storylet = storylets_by_id[storylet_id]
            needed = needed_by_scene.setdefault(storylet.scene_id, set())
            needed.update(predicate.fact_id for predicate in storylet.activation_conditions)
            needed.update(
                predicate.fact_id
                for knowledge in knowledge_by_storylet.get(storylet_id, ())
                for predicate in knowledge.requires
            )

        for storylet in package.storylet_routes.storylets:
            if storylet.id in required or not needed_by_scene.get(storylet.scene_id):
                continue
            if any(
                operation.op == "assert" and operation.fact_id in needed_by_scene[storylet.scene_id]
                for realization in storylet.realizations
                for operation in realization.operations
            ):
                required.add(storylet.id)
                changed = True

    return frozenset(required)
