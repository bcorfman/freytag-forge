"""Convert the loaded package's facts and placements to source documents."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from storygame.story_package.models import StoryPackage


@dataclass(frozen=True)
class FactsResult:
    """The scene-owned and unplaced fact source documents."""

    scene_docs: dict[str, dict]
    unplaced_facts: dict


def convert_facts(package: StoryPackage) -> FactsResult:
    """Convert package facts and placements without retaining reader-only prose."""

    scenes = tuple((scene.metadata.scene_id, scene) for scene in package.scenes)
    fact_ids = _ordered_fact_ids(package)
    effects, conditions = _fact_uses(package, scenes)
    owners = _owners(fact_ids, scenes, effects, conditions)
    declarations = {fact.id: {"purpose": fact.purpose} for fact in package.knowledge.facts}
    _merge_declarations(declarations, _fact_effects(package, fact_ids))
    _merge_declarations(declarations, _fact_deliveries(package, fact_ids, owners))
    scene_docs = {scene_id: {"facts": {}, "placements": _placements(scene)} for scene_id, scene in scenes}
    unplaced: dict[str, dict[str, Any]] = {}
    for fact_id in fact_ids:
        declaration = declarations[fact_id]
        owner = owners.get(fact_id)
        if owner is None:
            unplaced[fact_id] = declaration
        else:
            scene_docs[owner]["facts"][fact_id] = declaration
    return FactsResult(scene_docs=scene_docs, unplaced_facts=unplaced)


def _ordered_fact_ids(package: StoryPackage) -> tuple[str, ...]:
    """Keep source-declared fact order while removing generated entry facts."""

    entry_ids = {f"scene_{scene.metadata.scene_id.lower()}_entry_known" for scene in package.scenes}
    ids = list(dict.fromkeys(fact_id for fact_id in package.world.facts if fact_id not in entry_ids))
    known = set(ids)
    ids.extend(fact.id for fact in package.knowledge.facts if fact.id not in known and fact.id not in entry_ids)
    return tuple(ids)


def _fact_uses(package: StoryPackage, scenes: tuple[tuple[str, Any], ...]) -> tuple[dict, dict]:
    """Collect the effect and condition scenes represented in the package."""

    effects: dict[str, list[str]] = {}
    conditions: dict[str, list[str]] = {}
    for scene_id, scene in scenes:
        _add_conditions(conditions, scene_id, (item.requires for item in scene.metadata.entry_variants))
        for placement in scene.metadata.item_placements.values():
            _add_value(conditions, scene_id, getattr(placement, "while_fact_true", None))
            _add_value(conditions, scene_id, getattr(placement, "while_fact_false", None))
    for event in package.pacing.events:
        _add_predicates(conditions, event.scene_id, event.when)
        _add_predicates(effects, event.scene_id, event.effects)
    for route in package.storylet_routes.storylets:
        _add_conditions(conditions, route.scene_id, (route.activation_conditions,))
        for realization in route.realizations:
            _add_operations(effects, route.scene_id, realization.operations)
    for claim in package.knowledge.knowledge:
        for scene_id in claim.available_in_scenes:
            _add_predicates(conditions, scene_id, claim.requires)
            _add_conditions(conditions, scene_id, (variant.requires for variant in claim.delivery_variants))
            _add_operations(effects, scene_id, claim.establishes)
    for delivery in package.deliveries:
        _add_operations(effects, delivery.scene_id, delivery.costs)
    for event in package.storylet_routes.bridge_events:
        _add_activation(conditions, event.scene_id, event.activation)
        _add_operations(effects, event.scene_id, event.operations)
    if package.pacing.ending is not None:
        ending = package.pacing.ending
        _add_predicates(conditions, ending.scene_id, ending.when)
        _add_conditions(conditions, ending.scene_id, (variant.requires for variant in ending.variants))
    for transition in package.pacing.transitions:
        _add_predicates(conditions, transition.source_scene_id, transition.triggers)
    return effects, conditions


def _owners(
    fact_ids: Iterable[str], scenes: tuple[tuple[str, Any], ...], effects: dict, conditions: dict
) -> dict[str, str]:
    """Assign each fact to its first effect scene, then its first condition scene."""

    order = {scene_id: index for index, (scene_id, _) in enumerate(scenes)}
    owners: dict[str, str] = {}
    for fact_id in fact_ids:
        candidates = effects.get(fact_id, ()) or conditions.get(fact_id, ())
        if candidates:
            owners[fact_id] = min(candidates, key=lambda scene_id: order.get(scene_id, len(order)))
    return owners


def _fact_effects(package: StoryPackage, fact_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Copy world on-assert effects into source declaration form."""

    result: dict[str, dict[str, Any]] = {}
    for fact_id in fact_ids:
        if fact_id not in package.world.fact_effects:
            continue
        effects = package.world.fact_effects.get(fact_id, ())
        result[fact_id] = {
            "purpose": _purpose(package, fact_id),
            "on_assert": [_model_dict(item) for item in effects],
        }
    return result


def _fact_deliveries(
    package: StoryPackage, fact_ids: Iterable[str], owners: dict[str, str]
) -> dict[str, dict[str, Any]]:
    """Copy fact delivery records, including only a non-default scene."""

    result: dict[str, dict[str, Any]] = {}
    for delivery in package.deliveries:
        record: dict[str, Any] = {}
        declaring_scene = owners.get(delivery.fact_id)
        if declaring_scene != delivery.scene_id:
            record["scene"] = delivery.scene_id
        record["source_kind"] = delivery.source_kind
        if delivery.source_entity_id is not None:
            record["source_entity"] = delivery.source_entity_id
        record["fallback_text"] = delivery.fallback_text
        if delivery.cue_text is not None:
            record["cue_text"] = delivery.cue_text
        if delivery.escalation_text is not None:
            record["escalation_text"] = delivery.escalation_text
        if delivery.costs:
            record["costs"] = _operations_dict(delivery.costs)
        result[delivery.fact_id] = {"purpose": _purpose(package, delivery.fact_id), "delivery": record}
    return {fact_id: result[fact_id] for fact_id in fact_ids if fact_id in result}


def _merge_declarations(target: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]]) -> None:
    """Merge independent declaration fields without dropping effects or delivery data."""

    for fact_id, declaration in updates.items():
        target.setdefault(fact_id, {}).update(declaration)


def _placements(scene: Any) -> dict[str, Any]:
    """Merge item and non-item placements in their per-kind package order."""

    result: dict[str, Any] = {}
    for entity_id, placement in scene.metadata.item_placements.items():
        result[entity_id] = _placement_value(placement)
    for entity_id, placement in scene.metadata.character_placements.items():
        result[entity_id] = _placement_value(placement)
    return result


def _placement_value(value: Any) -> Any:
    """Convert a placement model to the source mapping accepted by the compiler."""

    return value if isinstance(value, str) else _model_dict(value)


def _purpose(package: StoryPackage, fact_id: str) -> str:
    """Return the package's immutable purpose for a fact."""

    return next(fact.purpose for fact in package.knowledge.facts if fact.id == fact_id)


def _model_dict(value: Any) -> dict[str, Any]:
    """Dump a frozen package model using source aliases and meaningful values."""

    return value.model_dump(by_alias=True, exclude_none=True, exclude_defaults=True, mode="python")


def _add_value(target: dict[str, list[str]], scene_id: str, value: Any) -> None:
    """Add one scalar fact use when present."""

    if isinstance(value, str):
        target.setdefault(value, []).append(scene_id)


def _add_predicates(target: dict[str, list[str]], scene_id: str, predicates: Iterable[Any]) -> None:
    """Add fact IDs from model predicates."""

    for predicate in predicates:
        _add_value(target, scene_id, getattr(predicate, "fact_id", None))


def _add_conditions(target: dict[str, list[str]], scene_id: str, groups: Iterable[Iterable[Any]]) -> None:
    """Add fact IDs from several predicate groups."""

    for group in groups:
        _add_predicates(target, scene_id, group)


def _add_operations(target: dict[str, list[str]], scene_id: str, operations: Iterable[Any]) -> None:
    """Add fact IDs written by route operations."""

    for operation in operations:
        _add_value(target, scene_id, getattr(operation, "fact_id", None))


def _add_activation(target: dict[str, list[str]], scene_id: str, activation: Any) -> None:
    """Add facts read by a canonical event activation rule."""

    _add_conditions(target, scene_id, (activation.all_facts_true, activation.any_of))


def _operations_dict(operations: Iterable[Any]) -> dict[str, Any]:
    """Convert package route operations to the compiler's mapping form."""

    result: dict[str, Any] = {}
    for operation in operations:
        result[operation.fact_id] = "retract" if operation.op == "retract" else operation.value
    return result
