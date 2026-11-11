"""Shared fact dependency lookups for a loaded story package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from storygame.story_package.models import KnowledgeDefinition, StoryPackage


@dataclass(frozen=True)
class Producer:
    kind: str
    record_id: str
    scene_id: str | None
    text: str


@dataclass(frozen=True)
class Consumer:
    kind: Literal["gate", "wording", "world"]
    record_id: str
    text: str
    scene_id: str | None = None


def _operation_value(operation: object) -> object:
    value = getattr(operation, "value", None)
    return True if value is None else value


def _claim_source(claim: KnowledgeDefinition) -> str:
    source = claim.source
    return source.realization_id or source.storylet_id or source.kind


def producers(package: StoryPackage, fact_id: str, value: object = True) -> list[Producer]:
    result: list[Producer] = []
    for event in package.pacing.events:
        if any(effect.fact_id == fact_id and effect.equals == value for effect in event.effects):
            result.append(
                Producer(
                    "pacing event",
                    event.id,
                    event.scene_id,
                    f"pacing event {event.id} (turn {event.at_turn})",
                )
            )
    for claim in package.knowledge.knowledge:
        if any(effect.fact_id == fact_id and effect.value == value for effect in claim.establishes):
            result.append(Producer("claim", claim.id, None, f"claim {claim.id} from {_claim_source(claim)}"))
    for delivery in package.deliveries:
        if delivery.fact_id == fact_id and value is True:
            result.append(
                Producer(
                    "fallback handoff",
                    delivery.fact_id,
                    delivery.scene_id,
                    f"fallback handoff for {delivery.fact_id} (scene {delivery.scene_id})",
                )
            )
        if any(cost.fact_id == fact_id and _operation_value(cost) == value for cost in delivery.costs):
            result.append(
                Producer(
                    "fallback handoff",
                    delivery.fact_id,
                    delivery.scene_id,
                    f"fallback handoff for {delivery.fact_id} (scene {delivery.scene_id})",
                )
            )
    for event in (*package.storylet_routes.bridge_events, *package.storylet_routes.resolution_events):
        operation_match = any(
            operation.op == "assert" and operation.fact_id == fact_id and _operation_value(operation) == value
            for operation in event.operations
        )
        activation_match = (
            event in package.storylet_routes.bridge_events
            and value is True
            and fact_id in (*event.activation.all_facts_true, *event.activation.any_of)
            and not any(
                knowledge.audience.player_visible and effect.fact_id == fact_id
                for knowledge in package.knowledge.knowledge
                for effect in knowledge.establishes
            )
        )
        if operation_match or activation_match:
            result.append(
                Producer(
                    "canonical route event",
                    event.id,
                    event.scene_id,
                    f"canonical route event {event.id}",
                )
            )
    for storylet in package.storylet_routes.storylets:
        for realization in storylet.realizations:
            if any(
                operation.op == "assert" and operation.fact_id == fact_id and _operation_value(operation) == value
                for operation in realization.operations
            ):
                result.append(
                    Producer(
                        "storylet realization",
                        realization.id,
                        storylet.scene_id,
                        f"storylet {storylet.id} realization {realization.id}",
                    )
                )
    for connection in package.connections:
        if any(
            operation.op == "assert" and operation.fact_id == fact_id and _operation_value(operation) == value
            for operation in connection.consequences
        ):
            result.append(
                Producer(
                    "connection consequence",
                    connection.id,
                    None,
                    f"connection {connection.id} consequence",
                )
            )
    for scene in package.scenes:
        entry_fact = f"scene_{scene.metadata.scene_id.lower()}_entry_known"
        if entry_fact == fact_id and value is True:
            result.append(
                Producer(
                    "scene entry",
                    scene.metadata.scene_id,
                    scene.metadata.scene_id,
                    f"scene entry fact for {scene.metadata.scene_id}",
                )
            )
    return result


def consumers(package: StoryPackage, fact_id: str, exclude_transition_id: str | None = None) -> list[Consumer]:
    result: list[Consumer] = []
    for event in package.pacing.events:
        if any(condition.fact_id == fact_id for condition in event.when):
            result.append(Consumer("gate", event.id, f"pacing event {event.id} waits on it", event.scene_id))
        for realization in event.realizations:
            if any(condition.fact_id == fact_id for condition in realization.when):
                result.append(
                    Consumer(
                        "wording",
                        event.id,
                        f"pacing event {event.id} (scene {event.scene_id}) picks a line of wording by it",
                        event.scene_id,
                    )
                )
    for transition in package.pacing.transitions:
        if transition.id != exclude_transition_id and any(
            trigger.fact_id == fact_id for trigger in transition.triggers
        ):
            result.append(
                Consumer("gate", transition.id, f"transition {transition.id} requires it", transition.source_scene_id)
            )
    for storylet in package.storylet_routes.storylets:
        if any(condition.fact_id == fact_id for condition in storylet.activation_conditions):
            result.append(
                Consumer("gate", storylet.id, f"storylet {storylet.id} activation depends on it", storylet.scene_id)
            )
    for event in (*package.storylet_routes.bridge_events, *package.storylet_routes.resolution_events):
        if fact_id in (*event.activation.all_facts_true, *event.activation.any_of):
            result.append(
                Consumer("gate", event.id, f"canonical route event {event.id} activation depends on it", event.scene_id)
            )
    for claim in package.knowledge.knowledge:
        if any(requirement.fact_id == fact_id for requirement in claim.requires):
            scene_id = claim.available_in_scenes[0] if len(claim.available_in_scenes) == 1 else None
            result.append(Consumer("gate", claim.id, f"claim {claim.id} requires it", scene_id))
        if any(fact_id in variant.requires for variant in claim.delivery_variants):
            scene_id = claim.available_in_scenes[0] if len(claim.available_in_scenes) == 1 else None
            result.append(Consumer("wording", claim.id, f"claim {claim.id} picks delivery wording by it", scene_id))
    for scene in package.scenes:
        if any(fact_id in variant.requires for variant in scene.metadata.entry_variants):
            result.append(
                Consumer(
                    "wording",
                    scene.metadata.scene_id,
                    f"scene {scene.metadata.scene_id} picks entry wording by it",
                    scene.metadata.scene_id,
                )
            )
        for item_id, placement in scene.metadata.item_placements.items():
            if (
                getattr(placement, "while_fact_false", None) == fact_id
                or getattr(placement, "while_fact_true", None) == fact_id
            ):
                result.append(
                    Consumer("gate", item_id, f"item {item_id} visibility depends on it", scene.metadata.scene_id)
                )
    for connection in package.connections:
        if connection.access_fact_id == fact_id:
            result.append(Consumer("gate", connection.id, f"connection {connection.id} requires it"))
    if package.pacing.ending is not None:
        ending = package.pacing.ending
        if any(condition.fact_id == fact_id for condition in ending.when):
            result.append(
                Consumer("gate", ending.scene_id, f"ending in scene {ending.scene_id} requires it", ending.scene_id)
            )
        if any(fact_id in variant.requires for variant in ending.variants):
            result.append(
                Consumer(
                    "wording",
                    ending.scene_id,
                    f"ending in scene {ending.scene_id} picks wording by it",
                    ending.scene_id,
                )
            )
    for guard in package.world.disclosure_guards:
        if guard.unlock_fact == fact_id:
            result.append(Consumer("world", guard.id, f"guard {guard.id} unlocks on it"))
    if package.world.fact_effects.get(fact_id):
        result.append(Consumer("world", fact_id, "world effect runs when it is asserted"))
    return result
