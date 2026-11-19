"""Convert legacy within-scene record order into explicit source order."""

from __future__ import annotations

from collections.abc import Mapping

from storygame.story_package.models import StoryPackage

from .convert_facts import FactsResult, convert_facts
from .convert_reveals import RevealsResult, convert_reveals
from .convert_scene import SceneResult, convert_scenes


def _by_scene(items: list[str], scene_for: Mapping[str, str], scene_ids: list[str]) -> dict[str, list[str]]:
    result = {scene_id: [] for scene_id in scene_ids}
    for item_id in items:
        result.setdefault(scene_for[item_id], []).append(item_id)
    return result


def _changed_order(legacy: list[str], natural: list[str]) -> list[str] | None:
    return legacy if legacy != natural else None


def _knowledge_natural(reveals: RevealsResult, scenes: SceneResult, scene_ids: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {scene_id: [] for scene_id in scene_ids}
    for scene_id in scene_ids:
        seen: set[str] = set()
        for document in (reveals.match_docs.get(scene_id, {}), scenes.match_docs.get(scene_id, {})):
            for claim_id in document.get("claims", {}):
                if claim_id not in seen:
                    result[scene_id].append(claim_id)
                    seen.add(claim_id)
    return result


def convert_order(
    package: StoryPackage,
    *,
    facts: FactsResult | None = None,
    reveals: RevealsResult | None = None,
    scenes: SceneResult | None = None,
) -> dict[str, dict[str, list[str]]]:
    """Return only scene/kind orders that differ from source conversion order."""

    scene_ids = [scene.metadata.scene_id for scene in package.scenes]
    result: dict[str, dict[str, list[str]]] = {scene_id: {} for scene_id in scene_ids}

    storylet_scenes = {item.id: item.scene_id for item in package.storylets}
    legacy_storylets = _by_scene([item.id for item in package.storylets], storylet_scenes, scene_ids)
    natural_storylets = _by_scene([item.id for item in package.storylet_routes.storylets], storylet_scenes, scene_ids)
    for scene_id in scene_ids:
        if order := _changed_order(legacy_storylets[scene_id], natural_storylets[scene_id]):
            result[scene_id]["storylets"] = order

    facts = facts or convert_facts(package)
    natural_deliveries: list[str] = []
    for scene_id in scene_ids:
        natural_deliveries.extend(
            fact_id for fact_id, declaration in facts.scene_docs[scene_id]["facts"].items() if "delivery" in declaration
        )
    delivery_scenes = {item.fact_id: item.scene_id for item in package.deliveries}
    legacy_deliveries = _by_scene([item.fact_id for item in package.deliveries], delivery_scenes, scene_ids)
    natural_delivery_groups = _by_scene(natural_deliveries, delivery_scenes, scene_ids)
    for scene_id in scene_ids:
        if order := _changed_order(legacy_deliveries[scene_id], natural_delivery_groups[scene_id]):
            result[scene_id]["deliveries"] = order

    reveals = reveals or convert_reveals(package)
    scenes = scenes or convert_scenes(package)
    natural_knowledge = _knowledge_natural(reveals, scenes, scene_ids)
    claim_scenes = {
        claim.id: claim.available_in_scenes[0] for claim in package.knowledge.knowledge if claim.available_in_scenes
    }
    legacy_knowledge = _by_scene(
        [claim.id for claim in package.knowledge.knowledge if claim.id in claim_scenes], claim_scenes, scene_ids
    )
    for scene_id in scene_ids:
        if order := _changed_order(legacy_knowledge[scene_id], natural_knowledge[scene_id]):
            result[scene_id]["knowledge"] = order

    event_scenes = {item.id: item.scene_id for item in package.pacing.events}
    legacy_events = _by_scene([item.id for item in package.pacing.events], event_scenes, scene_ids)
    natural_events = {
        scene_id: [event["id"] for event in scenes.scene_docs[scene_id].get("beats", ())] for scene_id in scene_ids
    }
    for scene_id in scene_ids:
        if order := _changed_order(legacy_events[scene_id], natural_events[scene_id]):
            result[scene_id]["pacing_events"] = order

    return {scene_id: order for scene_id, order in result.items() if order}
