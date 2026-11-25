"""Build the story-agnostic scene input required by the outcome contract."""

from __future__ import annotations

from typing import Any


def build_contract_scene(package: Any, scene_id: str) -> dict[str, Any]:
    """Project an immutable story package into one outcome-contract scene."""
    scenes = package.scenes
    scene_ids = [scene.metadata.scene_id for scene in scenes]
    if scene_id not in scene_ids:
        raise ValueError(f"unknown scene id: {scene_id}")

    scene_index = scene_ids.index(scene_id)
    available_before = set(scene_ids[:scene_index])
    delivered_before: set[str] = set()
    for item in package.knowledge.knowledge:
        available = set(item.available_in_scenes)
        if available & available_before and scene_id not in available:
            delivered_before.add(item.id)
        if (
            item.source.kind not in {"storylet_realization", "canonical_route_event"}
            and item.available_in_scenes[0] == scene_id
        ):
            delivered_before.add(item.id)

    candidates = set(package.knowledge_indexes.scene_to_candidates.get(scene_id, ()))
    pacing_window = next(
        (window.handoff_after_turns for window in package.pacing.scenes if window.scene_id == scene_id),
        None,
    )
    ending = package.pacing.ending
    terminal = ending is not None and ending.scene_id == scene_id
    ending_requires = sorted(predicate.fact_id for predicate in ending.when) if terminal and ending else []

    return {
        "id": scene_id,
        "pacing_window": pacing_window,
        "terminal": terminal,
        "reveal_ids": sorted(candidates - delivered_before),
        "delivered_before": sorted(delivered_before),
        "ending_requires": ending_requires,
        "non_voiceable_says": [],
        "unlearned_terms": [],
        "epilogue_candidates": [],
    }
