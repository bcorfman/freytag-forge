"""Build the story-aware view sent to the bench judges."""

from __future__ import annotations

from typing import Any

from bench.item_facts import declared_axes_for_package
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
    hidden = {item.id for item in package.world.items if item.hidden}
    revealed_by_effect = {
        effect.reveal
        for fact_id in facts
        for effect in package.world.fact_effects.get(fact_id, ())
        if effect.reveal is not None
    }
    return {
        item_names[item_id]
        for item_id, placement in scene.metadata.item_placements.items()
        if isinstance(placement, ItemPlacement)
        and placement.while_fact_true in facts
        and item_id in item_names
        and (item_id not in hidden or item_id in revealed_by_effect)
    } | {item_names[item_id] for item_id in revealed_by_effect if item_id in item_names}


def _narrator_narration(narration: str, story_text: list[str]) -> str:
    remaining = narration
    for authored in reversed(story_text):
        candidate = remaining.rstrip()
        if not candidate.endswith(authored):
            return narration
        remaining = candidate[: -len(authored)]
    return remaining.rstrip()


def _place_contents(turn: dict[str, Any], package: StoryPackage) -> dict[str, list[str]]:
    """Project the authored and recorded containment for the turn's scene."""

    scene = next((scene for scene in package.scenes if scene.metadata.scene_id == turn.get("scene_id")), None)
    if scene is None:
        return {}

    entities = []
    seen_entity_ids: set[str] = set()
    for entity in [*package.world.locations, *package.world.items, *package.world.npcs, *package.characters]:
        if entity.id not in seen_entity_ids:
            entities.append(entity)
            seen_entity_ids.add(entity.id)
    nodes: list[str] = [entity.id for entity in entities]
    package_by_id = {entity.id: entity for entity in entities}
    name_to_id: dict[str, str] = {}
    for entity in entities:
        for name in (entity.name, *getattr(entity, "aliases", ())):
            name_to_id.setdefault(name.casefold(), entity.id)

    def new_node(name: str) -> str:
        node_id = f"__judge_node_{len(nodes)}"
        nodes.append(node_id)
        node_names[node_id] = name
        return node_id

    node_names: dict[str, str] = {entity.id: entity.name for entity in entities}
    tracked_names: dict[str, str] = {}

    def resolve(name: str, *, create: bool = True) -> str | None:
        folded = name.casefold()
        node_id = name_to_id.get(folded)
        if node_id is None and create:
            node_id = new_node(name)
            name_to_id[folded] = node_id
        return node_id

    # A tracked name and each name learned for it are all names for one node.
    # Bind the whole group at once so an alias can identify a package entity.
    item_name_groups = turn.get("item_facts_names", {})
    if isinstance(item_name_groups, dict):
        for tracked_name, other_names in item_name_groups.items():
            if not isinstance(tracked_name, str):
                continue
            names = [tracked_name, *(other_names if isinstance(other_names, list) else [])]
            node_id = next((name_to_id.get(name.casefold()) for name in names if isinstance(name, str)), None)
            if node_id is None:
                node_id = new_node(tracked_name)
            for name in names:
                if isinstance(name, str):
                    name_to_id[name.casefold()] = node_id

    before = turn.get("item_facts_before", {})
    after = turn.get("item_facts_after", {})
    if isinstance(before, dict):
        for name in before:
            if isinstance(name, str):
                node_id = resolve(name)
                if node_id is not None:
                    tracked_names.setdefault(node_id, name)
    if isinstance(after, dict):
        for name in after:
            if isinstance(name, str):
                node_id = resolve(name)
                if node_id is not None:
                    tracked_names[node_id] = name

    authored_parent_of: dict[str, str] = {
        entity.id: entity.parent for entity in package.world.locations if entity.parent is not None
    }
    for item_id, placement in scene.metadata.item_placements.items():
        if isinstance(placement, ItemPlacement) and placement.parent is not None:
            authored_parent_of[item_id] = placement.parent
    for character_id, placement in scene.metadata.character_placements.items():
        authored_parent_of[character_id] = placement.parent

    parent_of = {node_id: parent for node_id, parent in authored_parent_of.items()}
    recorded_ids: set[str] = set()
    if isinstance(after, dict):
        for item_name, facts in after.items():
            if not isinstance(item_name, str):
                continue
            item_id = resolve(item_name)
            if item_id is None:
                continue
            recorded_ids.add(item_id)
            if not isinstance(facts, dict) or not isinstance(facts.get("place"), str):
                continue
            parent_of[item_id] = resolve(facts["place"])

    hidden_ids = {item.id for item in package.world.items if item.hidden}

    def allowed(node_id: str) -> bool:
        return node_id not in hidden_ids or node_id in recorded_ids

    def is_inside(node_id: str, place_id: str) -> bool:
        current = node_id
        trail: set[str] = set()
        while current not in trail:
            trail.add(current)
            parent = parent_of.get(current)
            if parent is None:
                return False
            if parent == place_id:
                return True
            current = parent
        return False

    def display_name(node_id: str) -> str:
        return tracked_names.get(node_id, node_names[node_id])

    contents: dict[str, list[str]] = {}
    for place_id in nodes:
        if not allowed(place_id):
            continue
        values = [display_name(node_id) for node_id in nodes if allowed(node_id) and is_inside(node_id, place_id)]
        contents[display_name(place_id)] = values
        entity = package_by_id.get(place_id)
        if entity is not None:
            for name in (entity.name, *getattr(entity, "aliases", ())):
                contents[name] = values
    return contents


def _place_names(turn: dict[str, Any], package: StoryPackage) -> dict[str, list[str]]:
    """Map recorded place labels to the package location names they identify."""

    locations_by_name: dict[str, tuple[str, list[str]]] = {}
    for location in package.world.locations:
        names = [location.name, *getattr(location, "aliases", ())]
        for name in names:
            locations_by_name.setdefault(name.casefold(), (location.name, list(getattr(location, "aliases", ()))))

    result: dict[str, list[str]] = {}
    for facts in (turn.get("item_facts_before", {}), turn.get("item_facts_after", {})):
        if not isinstance(facts, dict):
            continue
        for entry in facts.values():
            if not isinstance(entry, dict) or not isinstance(entry.get("place"), str):
                continue
            label = entry["place"]
            location = locations_by_name.get(label.casefold())
            if location is not None:
                name, aliases = location
                result[label] = [name, *aliases]
    return result


def _person_places(turn: dict[str, Any], package: StoryPackage) -> list[str]:
    """Return recorded place labels that identify a package character."""

    person_names = {
        name.casefold()
        for person in package.world.npcs
        for name in (person.name, *getattr(person, "aliases", ()), getattr(person, "unnamed_label", None))
        if name is not None
    }
    result: set[str] = set()
    for facts in (turn.get("item_facts_before", {}), turn.get("item_facts_after", {})):
        if not isinstance(facts, dict):
            continue
        for entry in facts.values():
            if not isinstance(entry, dict) or not isinstance(entry.get("place"), str):
                continue
            label = entry["place"]
            if label.casefold() in person_names:
                result.add(label)
    return sorted(result)


def judge_turns(
    turns: list[dict[str, Any]],
    scene_transitions: list[dict[str, Any]],
    package: StoryPackage,
    *,
    state_axes: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return judge views without changing the saved turn records."""

    judged: list[dict[str, Any]] = []
    for turn in turns:
        copy = dict(turn)
        typed_input = turn["typed_input"] if "typed_input" in turn else turn.get("player_input", "")
        player_input = turn.get("player_input", "")
        copy["command_typed"] = typed_input
        copy["just_before"] = (
            player_input[: -len(typed_input)].strip()
            if isinstance(player_input, str)
            and isinstance(typed_input, str)
            and typed_input
            and len(player_input) > len(typed_input)
            and player_input.endswith(typed_input)
            else ""
        )
        copy["story_text"] = _story_text(turn, scene_transitions, package)
        copy["narrator_narration"] = _narrator_narration(copy["narration"], copy["story_text"])
        copy["command"] = typed_input
        copy["turn_text"] = [
            *([{"by": "game", "text": copy["just_before"]}] if copy["just_before"] else []),
            *([{"by": "narrator", "text": copy["narrator_narration"]}] if copy["narrator_narration"] else []),
            *([{"by": "story", "text": text} for text in copy["story_text"]]),
        ]
        copy["place_contents"] = _place_contents(turn, package)
        copy["place_names"] = _place_names(turn, package)
        copy["person_places"] = _person_places(turn, package)
        copy["item_facts_names"] = turn.get("item_facts_names", {})
        before = dict(turn.get("item_facts_before", {}))
        after = dict(turn.get("item_facts_after", {}))
        names = {*before, *after}
        item_facts_axes = turn.get("item_facts_axes")
        if item_facts_axes is None:
            item_facts_axes = declared_axes_for_package(package, names, state_axes)
        else:
            item_facts_axes = {
                name: [list(poles) for poles in axes] for name, axes in item_facts_axes.items() if name in names
            }
        declared_poles = {
            name: {pole.casefold() for axis in axes for pole in axis} for name, axes in item_facts_axes.items()
        }

        def judge_facts(facts, *, poles=declared_poles):
            result = {}
            for name, entry in facts.items():
                if not isinstance(entry, dict):
                    result[name] = entry
                    continue
                judged_entry = dict(entry)
                conditions = entry.get("condition")
                if isinstance(conditions, list):
                    judged_entry["condition"] = [
                        condition
                        for condition in conditions
                        if isinstance(condition, str) and condition.casefold() in poles.get(name, set())
                    ]
                result[name] = judged_entry
            return result

        for item_name in _revealed_item_names(turn, package):
            before.pop(item_name, None)
        copy["item_facts_axes"] = item_facts_axes
        copy["item_facts_before"] = judge_facts(before)
        copy["item_facts_after"] = judge_facts(after)
        judged.append(copy)
    return judged
