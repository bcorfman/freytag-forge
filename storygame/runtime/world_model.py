"""The storygame adapter for the story-agnostic worldkeeper library."""

import logging
from dataclasses import dataclass

from worldkeeper import World, WorldSchema

from storygame.runtime.facts import Fact, FactStore
from storygame.story_package.models import StoryPackage, WorldEffect
from storygame.story_package.world_schema import world_source_schema_data

WORLD_EFFECTS_APPLIED = "world_effects_applied"


@dataclass(frozen=True)
class WorldEffectRefusal:
    fact_id: str
    effect: dict
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
        result = {"move": effect.move, "parent": effect.parent, "under": effect.under}
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
