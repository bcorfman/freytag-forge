from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from storygame.story_package.loader import load_story_package
from storygame.story_package.obligations import required_storylet_ids

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _old_required_ids(package) -> set[str]:
    bridge_facts_by_scene: dict[str, set[str]] = {}
    for event in package.storylet_routes.bridge_events:
        bridge_facts_by_scene.setdefault(event.scene_id, set()).update(event.activation.all_facts_true)
        bridge_facts_by_scene[event.scene_id].update(event.activation.any_of)
    resolution_ids = {
        storylet_id
        for event in package.storylet_routes.resolution_events
        for storylet_id in event.realization_storylets
    }
    return {
        storylet.id
        for storylet in package.storylet_routes.storylets
        if storylet.id in resolution_ids
        or any(
            operation.fact_id in bridge_facts_by_scene.get(storylet.scene_id, set())
            for realization in storylet.realizations
            for operation in realization.operations
        )
    }


def _synthetic_package():
    def operation(op: str, fact_id: str):
        return SimpleNamespace(op=op, fact_id=fact_id)

    def storylet(storylet_id: str, scene_id: str, operations=(), conditions=()):
        return SimpleNamespace(
            id=storylet_id,
            scene_id=scene_id,
            activation_conditions=tuple(SimpleNamespace(fact_id=fact_id) for fact_id in conditions),
            realizations=(SimpleNamespace(operations=tuple(operations)),),
        )

    required = storylet("SL-1A-A", "1A", conditions=("needed_by_condition",))
    producer = storylet(
        "SL-1A-B",
        "1A",
        operations=(
            operation("assert", "needed_by_condition"),
            operation("assert", "needed_by_knowledge"),
        ),
    )
    unrelated = storylet("SL-1A-C", "1A", operations=(operation("assert", "unrelated"),))
    other_scene = storylet("SL-1B-A", "1B", operations=(operation("assert", "needed_by_condition"),))
    source = SimpleNamespace(storylet_id="SL-1A-A")
    knowledge = SimpleNamespace(
        source=source,
        requires=(SimpleNamespace(fact_id="needed_by_knowledge"),),
    )
    routes = SimpleNamespace(
        storylets=(required, producer, unrelated, other_scene),
        bridge_events=(),
        resolution_events=(SimpleNamespace(realization_storylets=("SL-1A-A",)),),
    )
    return SimpleNamespace(
        storylet_routes=routes,
        knowledge_indexes=SimpleNamespace(by_id={"k-required": knowledge}),
    )


def test_real_package_keeps_old_required_storylets_and_adds_prerequisite_closure() -> None:
    required = required_storylet_ids(PACKAGE)
    old = _old_required_ids(PACKAGE)

    assert len(old) == 28
    assert old <= required
    assert required - old == {"SL-1A-E", "SL-2A-E", "SL-3A-B", "SL-3B-E"}
    assert len(required) == 32


def test_optional_same_scene_producer_is_pulled_into_closure() -> None:
    required = required_storylet_ids(_synthetic_package())

    assert required == {"SL-1A-A", "SL-1A-B"}


def test_producer_in_different_scene_is_not_pulled_into_closure() -> None:
    assert "SL-1B-A" not in required_storylet_ids(_synthetic_package())
