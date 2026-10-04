"""Build and check a story package's scene affordance map."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from storygame.story_package.loader import load_story_package


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, Mapping):
        return {key: _dump(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump(item) for item in value]
    return value


def _predicate(predicate: Any) -> dict[str, Any]:
    return {"fact_id": predicate.fact_id, "equals": predicate.equals}


def _true_operations(operations: Iterable[Any]) -> set[str]:
    return {op.fact_id for op in operations if op.op == "assert" and op.value is True}


def _entities(package: Any) -> dict[str, Any]:
    return {
        entity.id: entity
        for entity in (*package.world.locations, *package.world.npcs, *package.world.groups, *package.world.items)
    }


def _entity_kind(entity: Any) -> str:
    name = type(entity).__name__
    return {"Location": "location", "Npc": "npc", "Group": "group", "Item": "item"}.get(name, "item")


def _find_entities(package: Any, term: str) -> list[str]:
    pattern = re.compile(r"(?<!\w)" + re.escape(term.strip()) + r"(?!\w)", re.IGNORECASE)
    return [
        entity_id
        for entity_id, entity in _entities(package).items()
        if any(pattern.search(form) for form in (entity.name, *entity.aliases))
    ]


def _source_id(kind: str, value: str, suffix: str = "") -> str:
    return f"{kind}:{value}{':' + suffix if suffix else ''}"


def _source_text(source: dict[str, Any]) -> list[str]:
    return [text for text in (source.get("must_convey_texts", []) + source.get("delivery_texts", [])) if text]


def _entry_material(package: Any, scene: Any) -> list[dict[str, str]]:
    metadata = scene.metadata
    material = [{"label": "entry_text", "text": metadata.entry_text}]
    frame = next((frame for frame in package.knowledge.scene_frames if frame.scene_id == metadata.scene_id), None)
    if frame is not None:
        material.append({"label": "scene_frame_situation", "text": frame.situation})
    material.append({"label": "opening_beat_prose", "text": scene.opening_beat.prose})
    material.extend({"label": "opening_beat_detail", "text": text} for text in scene.opening_beat.details)
    for beat in scene.beats.values():
        material.extend({"label": "beat_detail", "text": text} for text in beat.details)
    for placement in metadata.item_placements.values():
        text = getattr(placement, "placement", None) or getattr(placement, "text", None) or placement
        material.append({"label": "item_placement", "text": str(text)})
    material.extend(
        {"label": "character_placement", "text": placement.text}
        for placement in metadata.character_placements.values()
        if placement.text
    )
    material.extend({"label": "bridge_text", "text": text} for text in metadata.bridge_text.values())
    for transition in package.pacing.transitions:
        if transition.target_scene_id != metadata.scene_id:
            continue
        previous = next(
            (candidate for candidate in package.scenes if candidate.metadata.scene_id == transition.source_scene_id),
            None,
        )
        if previous is not None and transition.id in previous.metadata.bridge_text:
            material.append({"label": "bridge_text_in", "text": previous.metadata.bridge_text[transition.id]})
    return [entry for entry in material if entry["text"]]


def _base_sources(package: Any, scene_id: str) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for known in package.knowledge.knowledge:
        if scene_id not in known.available_in_scenes:
            continue
        facts = _true_operations(known.establishes)
        if not facts:
            continue
        route = next(
            (candidate for candidate in package.storylet_routes.storylets if candidate.id == known.source.storylet_id),
            None,
        )
        sources.append(
            {
                "id": known.id,
                "kind": "knowledge",
                "facts": facts,
                "player_earned": known.earn_when is not None,
                "earn_when": known.earn_when,
                "requires_predicates": list(known.requires),
                "entity_ids": list(known.entity_ids),
                "action_evidence": [list(group) for group in known.action_evidence],
                "must_convey_texts": [" ".join(group) for group in known.must_convey],
                "delivery_texts": [known.delivery_text] if known.delivery_text else [],
                "earliest_turn": route.earliest_turn if route else None,
                "turn_window": {
                    "earliest": route.earliest_turn,
                    "target": route.target_turn,
                    "latest": route.latest_turn,
                }
                if route
                else None,
            }
        )
    for delivery in package.deliveries:
        if delivery.scene_id != scene_id:
            continue
        sources.append(
            {
                "id": _source_id("handoff", delivery.fact_id, scene_id),
                "kind": "handoff",
                "facts": {delivery.fact_id} | _true_operations(delivery.costs),
                "player_earned": False,
                "earn_when": None,
                "requires_predicates": [],
                "entity_ids": [delivery.source_entity_id] if delivery.source_entity_id else [],
                "action_evidence": [],
                "must_convey_texts": [" ".join(group) for group in delivery.must_convey],
                "delivery_texts": [delivery.fallback_text],
                "earliest_turn": None,
            }
        )
    for route in package.storylet_routes.storylets:
        if route.scene_id != scene_id:
            continue
        for realization in route.realizations:
            facts = _true_operations(realization.operations)
            if facts:
                sources.append(
                    {
                        "id": _source_id("storylet", route.id, realization.id),
                        "kind": "storylet",
                        "facts": facts,
                        "player_earned": True,
                        "earn_when": route.title,
                        "requires_predicates": list(route.activation_conditions),
                        "entity_ids": [],
                        "action_evidence": [],
                        "must_convey_texts": [],
                        "delivery_texts": [],
                        "earliest_turn": route.earliest_turn,
                        "turn_window": {
                            "earliest": route.earliest_turn,
                            "target": route.target_turn,
                            "latest": route.latest_turn,
                        },
                    }
                )
    for event in (*package.storylet_routes.bridge_events, *package.storylet_routes.resolution_events):
        if event.scene_id != scene_id:
            continue
        facts = _true_operations(event.operations)
        if facts:
            sources.append(
                {
                    "id": _source_id("storylet", event.id),
                    "kind": "storylet",
                    "facts": facts,
                    "player_earned": False,
                    "earn_when": None,
                    "requires_predicates": [],
                    "entity_ids": [],
                    "action_evidence": [],
                    "must_convey_texts": [],
                    "delivery_texts": [event.fallback_text] if event.fallback_text else [],
                    "earliest_turn": None,
                }
            )
    for event in package.pacing.events:
        if event.scene_id != scene_id:
            continue
        facts = {effect.fact_id for effect in event.effects if effect.equals is True}
        sources.append(
            {
                "id": event.id,
                "kind": "engine",
                "facts": facts,
                "player_earned": False,
                "earn_when": None,
                "requires_predicates": list(event.when),
                "entity_ids": [],
                "action_evidence": [],
                "must_convey_texts": [],
                "delivery_texts": [realization.text for realization in event.realizations],
                "earliest_turn": event.at_turn,
                "turn_window": {"earliest": event.at_turn, "target": event.at_turn, "latest": event.at_turn},
                "at_turn": event.at_turn,
                "when": [_predicate(condition) for condition in event.when],
                "realization_texts": [realization.text for realization in event.realizations],
            }
        )
    return sources


def _entry_guarantees(package: Any) -> dict[str, set[str]]:
    incoming: dict[str, set[str]] = {}
    for transition in package.pacing.transitions:
        incoming.setdefault(transition.target_scene_id, set()).add(transition.source_scene_id)
    result: dict[str, set[str]] = {}
    for scene_id, previous_ids in incoming.items():
        sets = []
        for previous_id in previous_ids:
            values = set()
            for event in package.storylet_routes.bridge_events:
                if event.scene_id == previous_id:
                    values.update(event.activation.all_facts_true)
                    values.update(_true_operations(event.operations))
            sets.append(values)
        if sets:
            result[scene_id] = set.intersection(*sets)
    return result


def _source_requires(
    source: dict[str, Any], by_fact: dict[str, list[dict[str, Any]]], entry: set[str], seen: set[str]
) -> list[dict[str, Any]]:
    result = []
    for predicate in source["requires_predicates"]:
        item = _predicate(predicate)
        producers = [] if predicate.fact_id in seen else by_fact.get(predicate.fact_id, [])
        item["sources"] = [producer["id"] for producer in producers]
        item["entry_guaranteed"] = predicate.fact_id in entry or predicate.fact_id in seen
        result.append(item)
    return result


def _affordances(
    package: Any,
    scene: Any,
    source: dict[str, Any],
    gate: str,
    order: dict[str, int],
    all_sources: list[dict[str, Any]],
    seen: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    seen = set() if seen is None else seen
    if source["id"] in seen:
        return [], []
    seen.add(source["id"])
    entity_ids = list(source["entity_ids"])
    unresolved: list[str] = []
    if source["action_evidence"]:
        for group in source["action_evidence"][1:]:
            matches = {entity_id for term in group for entity_id in _find_entities(package, term)}
            if matches:
                entity_ids.extend(matches)
            else:
                unresolved.append(" / ".join(group))
    entities = _entities(package)
    metadata = scene.metadata
    visible = {
        metadata.location_id,
        *metadata.participant_ids,
        *metadata.item_ids,
        *metadata.item_placements,
        *metadata.character_placements,
    }
    visible = {
        entity_id
        for entity_id in visible
        if entity_id in entities and not getattr(entities[entity_id], "hidden", False)
    }
    result = []
    earlier = [candidate for candidate in all_sources if order[candidate["id"]] < order[source["id"]]]
    for entity_id in dict.fromkeys(entity_ids):
        entity = entities.get(entity_id)
        if entity is None:
            unresolved.append(entity_id)
            continue
        revealed_by = next((candidate["id"] for candidate in earlier if entity_id in candidate["entity_ids"]), None)
        result.append(
            {
                "entity_id": entity_id,
                "name": entity.name,
                "kind": _entity_kind(entity),
                "gate": gate,
                "source": source["id"],
                "visible_at_entry": entity_id in visible,
                "revealed_by": revealed_by,
            }
        )
    return result, unresolved


def _collect_affordances(
    package: Any,
    scene: Any,
    source: dict[str, Any],
    gate: str,
    order: dict[str, int],
    sources: list[dict[str, Any]],
    by_fact: dict[str, list[dict[str, Any]]],
    seen: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    seen = set() if seen is None else seen
    if source["id"] in seen:
        return [], []
    direct, unresolved = _affordances(package, scene, source, gate, order, sources, seen)
    for predicate in source["requires_predicates"]:
        for required in by_fact.get(predicate.fact_id, []):
            nested, nested_unresolved = _collect_affordances(
                package, scene, required, gate, order, sources, by_fact, seen
            )
            direct.extend(nested)
            unresolved.extend(nested_unresolved)
    return direct, unresolved


def _serialize_source(
    package: Any,
    scene: Any,
    source: dict[str, Any],
    gate: str,
    order: dict[str, int],
    sources: list[dict[str, Any]],
    by_fact: dict[str, list[dict[str, Any]]],
    entry: set[str],
) -> dict[str, Any]:
    affordances, unresolved = _collect_affordances(package, scene, source, gate, order, sources, by_fact)
    unique_affordances = {}
    for affordance in affordances:
        unique_affordances.setdefault((affordance["entity_id"], affordance["source"]), affordance)
    requires = _source_requires(source, by_fact, entry, set())
    result = {
        "id": source["id"],
        "kind": source["kind"],
        "player_earned": source["player_earned"],
        "earn_when": source["earn_when"],
        "earliest_turn": source["earliest_turn"],
        "turn_window": source.get("turn_window"),
        "requires": requires,
        "affordances": list(unique_affordances.values()),
        "unresolved_terms": sorted(set(unresolved)),
    }
    if source["kind"] == "engine":
        result.update(
            {"at_turn": source["at_turn"], "when": source["when"], "realization_texts": source["realization_texts"]}
        )
    return result


def _gate_affordances(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose the source affordances once at gate level for map consumers."""
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for source in sources:
        for affordance in source["affordances"]:
            key = (affordance["entity_id"], affordance["source"])
            result.setdefault(key, affordance)
    return list(result.values())


def build_affordance_map(package: Any) -> dict[str, Any]:
    """Derive a JSON-compatible affordance map from a loaded package."""
    scenes = []
    guarantees = _entry_guarantees(package)
    for scene in package.scenes:
        scene_id = scene.metadata.scene_id
        sources = _base_sources(package, scene_id)
        order = {source["id"]: index for index, source in enumerate(sources)}
        by_fact: dict[str, list[dict[str, Any]]] = {}
        for source in sources:
            for fact_id in source["facts"]:
                by_fact.setdefault(fact_id, []).append(source)
        transitions = []
        for transition in package.pacing.transitions:
            if transition.source_scene_id != scene_id:
                continue
            transitions.append(
                {
                    "id": transition.id,
                    "target_scene_id": transition.target_scene_id,
                    "triggers": [_predicate(trigger) for trigger in transition.triggers],
                    "required_dependencies": list(transition.required_dependencies),
                }
            )
        gates = []
        for transition in package.pacing.transitions:
            if transition.source_scene_id != scene_id:
                continue
            for trigger in transition.triggers:
                if trigger.equals is True:
                    gate = f"{transition.id}:{trigger.fact_id}"
                    gate_sources = [
                        _serialize_source(
                            package,
                            scene,
                            source,
                            gate,
                            order,
                            sources,
                            by_fact,
                            guarantees.get(scene_id, set()) | {f"scene_{scene_id.lower()}_entry_known"},
                        )
                        for source in by_fact.get(trigger.fact_id, [])
                    ]
                    gates.append(
                        {
                            "transition_id": transition.id,
                            "fact_id": trigger.fact_id,
                            "sources": gate_sources,
                            "affordances": _gate_affordances(gate_sources),
                        }
                    )
        scenes.append(
            {
                "scene_id": scene_id,
                "entry_material": _entry_material(package, scene),
                "transitions": transitions,
                "gates": gates,
            }
        )
    return {"story_id": package.story_id, "scenes": scenes}


def _finding(check: int, scene_id: str, gate: str, subject: str, message: str) -> dict[str, Any]:
    return {"check": check, "scene_id": scene_id, "gate": gate, "subject": subject, "message": message}


def check_affordance_map(package: Any, amap: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for scene in amap["scenes"]:
        scene_id = scene["scene_id"]
        material = " ".join(entry["text"] for entry in scene["entry_material"]).casefold()
        for gate in scene["gates"]:
            gate_id = f"{gate['transition_id']}:{gate['fact_id']}"
            if not gate["sources"]:
                findings.append(_finding(1, scene_id, gate_id, gate["fact_id"], "trigger fact has no source"))
            for source in gate["sources"]:
                for requirement in source["requires"]:
                    if (
                        requirement["equals"] is True
                        and not requirement["sources"]
                        and not requirement["entry_guaranteed"]
                    ):
                        findings.append(
                            _finding(
                                1,
                                scene_id,
                                gate_id,
                                requirement["fact_id"],
                                "required fact has no local source or entry guarantee",
                            )
                        )
                if source["player_earned"]:
                    for affordance in source["affordances"]:
                        if not affordance["visible_at_entry"] and not affordance["revealed_by"]:
                            findings.append(
                                _finding(
                                    2,
                                    scene_id,
                                    gate_id,
                                    affordance["entity_id"],
                                    "player-earned affordance is neither visible nor revealed",
                                )
                            )
                        entity = next(
                            (
                                item
                                for item in (
                                    *package.world.locations,
                                    *package.world.npcs,
                                    *package.world.groups,
                                    *package.world.items,
                                )
                                if item.id == affordance["entity_id"]
                            ),
                            None,
                        )
                        forms = (entity.name, *entity.aliases) if entity else (affordance["name"],)
                        if not any(
                            re.search(r"(?<!\w)" + re.escape(form) + r"(?!\w)", material, re.IGNORECASE)
                            for form in forms
                        ):
                            earlier_text = " ".join(
                                text
                                for earlier_gate_source in gate["sources"]
                                if earlier_gate_source["id"] != source["id"]
                                for text in _source_text(earlier_gate_source)
                            )
                            if not any(
                                re.search(r"(?<!\w)" + re.escape(form) + r"(?!\w)", earlier_text, re.IGNORECASE)
                                for form in forms
                            ):
                                findings.append(
                                    _finding(
                                        3,
                                        scene_id,
                                        gate_id,
                                        affordance["entity_id"],
                                        "affordance is absent from entry and earlier source text",
                                    )
                                )
                if source["kind"] == "engine" and not source["realization_texts"]:
                    findings.append(
                        _finding(4, scene_id, gate_id, source["id"], "engine source has no realization text")
                    )
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for finding in findings:
        key = tuple(finding[field] for field in ("check", "scene_id", "gate", "subject"))
        unique.setdefault(key, finding)
    return list(unique.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--findings", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    package = load_story_package(args.package)
    amap = build_affordance_map(package)
    findings = check_affordance_map(package, amap)
    amap["findings"] = findings
    payload = json.dumps(amap, indent=2) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    for scene in amap["scenes"]:
        print(
            f"{scene['scene_id']}: {len(scene['transitions'])} transitions, {len(scene['gates'])} gates",
            file=sys.stderr,
        )
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
