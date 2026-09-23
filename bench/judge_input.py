"""Build the story-aware view sent to the bench judges."""

from __future__ import annotations

from typing import Any

from storygame.story_package.models import ItemPlacement, StoryPackage


def _story_text(turn: dict[str, Any], scene_transitions: list[dict[str, Any]], package: StoryPackage) -> list[str]:
    authored: list[str] = []
    candidate_id = turn.get("authored_handoff_candidate_id")
    if candidate_id is not None:
        delivery_text = package.knowledge_indexes.by_id[candidate_id].delivery_text
        if delivery_text is not None:
            authored.append(delivery_text)

    for transition_record in scene_transitions:
        if (
            transition_record.get("after_turn") == turn.get("turn_number")
            and transition_record.get("advanced_offline") is False
        ):
            transition = next(
                (
                    item
                    for item in package.pacing.transitions
                    if item.source_scene_id == transition_record.get("from_scene")
                    and item.target_scene_id == transition_record.get("to_scene")
                ),
                None,
            )
            if transition is not None:
                bridge = next(
                    scene.metadata.bridge_text.get(transition.id)
                    for scene in package.scenes
                    if scene.metadata.scene_id == transition.source_scene_id
                )
                if bridge is not None:
                    authored.append(bridge)
            break
    return authored


def _revealed_item_names(turn: dict[str, Any], package: StoryPackage) -> set[str]:
    candidate_id = turn.get("authored_handoff_candidate_id")
    if candidate_id is None:
        return set()
    knowledge = package.knowledge_indexes.by_id[candidate_id]
    facts = {effect.fact_id for effect in knowledge.establishes if effect.op == "assert" and effect.value is True}
    if not facts:
        return set()
    scene = next(
        (item for item in package.scenes if item.metadata.scene_id == turn.get("scene_id")),
        None,
    )
    if scene is None:
        return set()
    item_names = {item.id: item.name for item in package.world.items}
    return {
        item_names[item_id]
        for item_id, placement in scene.metadata.item_placements.items()
        if isinstance(placement, ItemPlacement) and placement.while_fact_true in facts and item_id in item_names
    }


def judge_turns(
    turns: list[dict[str, Any]], scene_transitions: list[dict[str, Any]], package: StoryPackage
) -> list[dict[str, Any]]:
    """Return judge views without changing the saved turn records."""

    judged: list[dict[str, Any]] = []
    for turn in turns:
        copy = dict(turn)
        copy["story_text"] = _story_text(turn, scene_transitions, package)
        before = dict(turn.get("item_facts_before", {}))
        for item_name in _revealed_item_names(turn, package):
            before.pop(item_name, None)
        copy["item_facts_before"] = before
        judged.append(copy)
    return judged
