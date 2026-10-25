"""Explain why a package reveal can or cannot be earned."""

from __future__ import annotations

from dataclasses import dataclass

from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import predicate_matches
from storygame.runtime.world_model import world_for
from storygame.story_package.models import KnowledgeDefinition

ELIGIBLE = "eligible"
ALREADY_ESTABLISHED = "already_established"
NOT_VISIBLE = "not_visible"
STORYLET_SPENT = "storylet_spent"
PREREQUISITE_MISSING = "prerequisite_missing"
NOT_REACHABLE = "not_reachable"
SOURCE_INACTIVE = "source_inactive"


@dataclass(frozen=True, slots=True)
class RevealEligibility:
    """The first runtime rule that decides a reveal's eligibility."""

    eligible: bool
    reason: str
    detail: str = ""


def _established(item: KnowledgeDefinition, state: RuntimeState) -> bool:
    def effect_matches(effect: object) -> bool:
        expected = str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value)
        matched = any(
            (fact.value if fact.value is not None else fact.object) == expected
            for fact in state.facts.matching(effect.fact_id)
        )
        return matched if effect.op == "assert" else not matched

    return all(effect_matches(effect) for effect in item.establishes)


def _visible_to(item: KnowledgeDefinition, audience_id: str) -> bool:
    if item.audience.kind == "world_only":
        return False
    if audience_id == "player":
        return item.audience.player_visible
    return item.audience.kind == "public" or audience_id in item.audience.character_ids


def together_or_unplaced(world, protagonist_id: str, entity_id: str) -> bool:
    """Treat an unplaced protagonist or an entity in the same root area as reachable."""
    protagonist_area = world.area(protagonist_id)
    if protagonist_area is None:
        return True
    if world.together(protagonist_id, entity_id):
        return True
    entity_area = world.area(entity_id)
    if entity_area is None:
        return False
    if world.kind(entity_id) == "area":
        return False
    protagonist_root = [protagonist_area, *world.chain(protagonist_area)][-1]
    entity_root = [entity_area, *world.chain(entity_area)][-1]
    return protagonist_root == entity_root


def explain_reveal(state: RuntimeState, audience_id: str, item: KnowledgeDefinition) -> RevealEligibility:
    """Return the first reason ``item`` is not an eligible reveal."""

    if _established(item, state):
        return RevealEligibility(False, ALREADY_ESTABLISHED, item.id)
    if not _visible_to(item, audience_id):
        return RevealEligibility(False, NOT_VISIBLE, audience_id)
    if item.source.storylet_id in state.fired_event_ids:
        return RevealEligibility(False, STORYLET_SPENT, item.source.storylet_id or "")
    for predicate in item.requires:
        if not predicate_matches(predicate, state.facts):
            return RevealEligibility(False, PREREQUISITE_MISSING, predicate.fact_id)
    if item.reach_entity_ids:
        world = world_for(state.package, state.facts)
        for entity_id in item.reach_entity_ids:
            if not together_or_unplaced(world, state.package.world.protagonist_id, entity_id):
                return RevealEligibility(False, NOT_REACHABLE, entity_id)
    if item.source.kind != "storylet_realization" or item.source.storylet_id not in state.active_event_ids:
        return RevealEligibility(False, SOURCE_INACTIVE, item.source.storylet_id or item.source.kind)
    return RevealEligibility(True, ELIGIBLE)
