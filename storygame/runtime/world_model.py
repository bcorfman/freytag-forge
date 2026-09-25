"""The storygame adapter for the story-agnostic worldkeeper library."""

import logging
from dataclasses import dataclass

from worldkeeper import World, WorldSchema

from storygame.runtime.facts import Fact, FactStore
from storygame.story_package.models import ItemPlacement, StoryPackage, WorldEffect
from storygame.story_package.world_schema import world_source_schema_data

WORLD_EFFECTS_APPLIED = "world_effects_applied"


@dataclass(frozen=True)
class WorldEffectRefusal:
    fact_id: str
    effect: dict
    reason: str


@dataclass(frozen=True)
class ScenePlacementRefusal:
    scene_id: str
    item_id: str
    parent_id: str
    reason: str


def world_schema_data(package: StoryPackage) -> dict:
    return world_source_schema_data(package.world)


def world_for(package: StoryPackage, facts: FactStore) -> World:
    return World(WorldSchema.from_data(world_schema_data(package)), facts, make_fact=Fact)


def _true(facts: FactStore, fact_id: str) -> bool:
    return any(str(fact.value).lower() == "true" for fact in facts.matching(fact_id, "story"))


def _marker_exists(facts: FactStore, fact_id: str) -> bool:
    return any(fact.object == fact_id for fact in facts.matching(WORLD_EFFECTS_APPLIED, "story"))


def pending_world_effects(package: StoryPackage, facts: FactStore) -> tuple[str, ...]:
    return tuple(
        fact_id
        for fact_id in package.world.facts
        if fact_id in package.world.fact_effects and _true(facts, fact_id) and not _marker_exists(facts, fact_id)
    )


def _effect_dict(effect: WorldEffect) -> dict:
    if effect.move is not None:
        result = {"move": effect.move, "parent": effect.parent, "under": effect.under, "text": effect.text}
    elif effect.reveal is not None:
        result = {"reveal": effect.reveal}
    elif effect.accompany is not None:
        result = {"accompany": effect.accompany, "with": effect.with_}
    else:
        result = {"set_axis": effect.set_axis, "value": effect.value}
    return result


def apply_world_effects(package: StoryPackage, facts: FactStore) -> tuple[WorldEffectRefusal, ...]:
    world = world_for(package, facts)
    refusals = []
    for fact_id in pending_world_effects(package, facts):
        for effect in package.world.fact_effects[fact_id]:
            effect_dict = _effect_dict(effect)
            result = world.apply_effects([effect_dict])[0]
            if not result.ok:
                refusal = WorldEffectRefusal(fact_id, effect_dict, result.reason)
                refusals.append(refusal)
                logging.getLogger(__name__).warning("world effect refused: %s", refusal)
        facts.assert_fact(Fact(predicate=WORLD_EFFECTS_APPLIED, subject="story", object=fact_id, value=None))
    return tuple(refusals)


def apply_scene_placements(package: StoryPackage, facts: FactStore, scene_id: str) -> tuple[ScenePlacementRefusal, ...]:
    world = world_for(package, facts)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    refusals = []
    result = world.place(package.world.protagonist_id, scene.metadata.location_id)
    if not result.ok:
        refusal = ScenePlacementRefusal(
            scene_id, package.world.protagonist_id, scene.metadata.location_id, result.reason
        )
        refusals.append(refusal)
        logging.getLogger(__name__).warning("scene placement refused: %s", refusal)
    for item_id, placement in scene.metadata.item_placements.items():
        if not isinstance(placement, ItemPlacement) or placement.parent is None:
            continue
        result = world.place(
            item_id,
            placement.parent,
            text=placement.text,
            under=placement.under,
            part_of=placement.part_of,
        )
        if not result.ok:
            refusal = ScenePlacementRefusal(scene_id, item_id, placement.parent, result.reason)
            refusals.append(refusal)
            logging.getLogger(__name__).warning("scene placement refused: %s", refusal)
    for character_id, placement in scene.metadata.character_placements.items():
        result = world.place(character_id, placement.parent, text=placement.text)
        if not result.ok:
            refusal = ScenePlacementRefusal(scene_id, character_id, placement.parent, result.reason)
            refusals.append(refusal)
            logging.getLogger(__name__).warning("scene placement refused: %s", refusal)
    for companion_id in world.companions(package.world.protagonist_id):
        result = world.clear_companion(companion_id)
        if not result.ok:
            refusal = ScenePlacementRefusal(scene_id, companion_id, world.parent(companion_id) or "", result.reason)
            refusals.append(refusal)
            logging.getLogger(__name__).warning("scene companion refused: %s", refusal)
    for companion_id in scene.metadata.companions:
        if companion_id not in scene.metadata.character_placements:
            parent_id = world.parent(package.world.protagonist_id)
            if parent_id is not None:
                result = world.place(companion_id, parent_id)
                if not result.ok:
                    refusal = ScenePlacementRefusal(scene_id, companion_id, parent_id, result.reason)
                    refusals.append(refusal)
                    logging.getLogger(__name__).warning("scene placement refused: %s", refusal)
        result = world.set_companion(companion_id, package.world.protagonist_id)
        if not result.ok:
            refusal = ScenePlacementRefusal(scene_id, companion_id, package.world.protagonist_id, result.reason)
            refusals.append(refusal)
            logging.getLogger(__name__).warning("scene companion refused: %s", refusal)
    return tuple(refusals)
