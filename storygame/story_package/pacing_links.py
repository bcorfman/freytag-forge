"""Validation for declared links between pacing events and knowledge items."""

from __future__ import annotations

from storygame.story_package.models import StoryPackage


def _item_facts(item: object) -> frozenset[str]:
    return frozenset(predicate.fact_id for predicate in item.requires) | frozenset(
        operation.fact_id for operation in item.establishes
    )


def _event_facts(event: object) -> frozenset[str]:
    return frozenset(effect.fact_id for effect in event.effects)


def _is_pressure_item(item: object) -> bool:
    return item.earn_when is None and not item.action_evidence and item.source.kind != "scene_entry"


def pacing_link_problems(package: StoryPackage) -> list[str]:
    """Return stable diagnostics for pacing-event knowledge declarations."""

    items = {item.id: item for item in package.knowledge.knowledge}
    events = tuple(package.pacing.events)
    problems: list[str] = []
    declared: dict[str, set[str]] = {item_id: set() for item_id in items}
    linkable: dict[str, set[str]] = {item.id: set() for item in package.knowledge.knowledge if _is_pressure_item(item)}

    for event in events:
        event_facts = _event_facts(event)
        for item_id in event.delivers:
            item = items.get(item_id)
            if item is None:
                problems.append(
                    f"event '{event.id}' declares unknown knowledge item '{item_id}'; change it to an existing item"
                )
                continue
            declared[item_id].add(event.id)
            if not _is_pressure_item(item):
                problems.append(
                    f"event '{event.id}' declares item '{item_id}', which is not a pressure item; "
                    "change the declaration"
                )
            if event.scene_id not in item.available_in_scenes:
                problems.append(
                    f"event '{event.id}' declares item '{item_id}', which is not available in event scene; "
                    "change the declaration"
                )
            if not event_facts & _item_facts(item):
                problems.append(
                    f"event '{event.id}' declares item '{item_id}', which shares no fact with its effects; "
                    "change the declaration"
                )

    for event in events:
        event_facts = _event_facts(event)
        for item in package.knowledge.knowledge:
            if (
                _is_pressure_item(item)
                and event.scene_id in item.available_in_scenes
                and event_facts & _item_facts(item)
            ):
                linkable[item.id].add(event.id)

    for item_id, event_ids in linkable.items():
        if event_ids and not declared[item_id] & event_ids:
            problems.append(
                f"pressure item '{item_id}' is an unlinked pacing-linked item; declare it on a linkable event"
            )
    return sorted(problems)
