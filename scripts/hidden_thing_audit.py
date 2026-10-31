from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from storygame.story_package import StoryPackageError  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402


def _forms(item: Any) -> tuple[str, ...]:
    return (item.name, *item.aliases, *item.scoped_aliases)


def _entities(package: Any) -> dict[str, Any]:
    world = package.world
    return {entity.id: entity for entity in (*world.locations, *world.npcs, *world.groups, *world.items)}


def _effective_fixed(package: Any, entity_id: str | None) -> bool | None:
    if entity_id is None:
        return None
    entity = _entities(package).get(entity_id)
    if entity is None:
        return None
    if hasattr(entity, "fixed") and entity.fixed is not None:
        return bool(entity.fixed)
    if not hasattr(entity, "kind"):
        return False
    world = package.world
    kinds = {kind.id: kind for kind in world.kinds}
    base_fixed = {"furniture": True}

    def fixed_for_kind(kind_id: str, seen: tuple[str, ...] = ()) -> bool | None:
        if kind_id in seen:
            return None
        declaration = kinds.get(kind_id)
        if declaration is not None and declaration.fixed is not None:
            return bool(declaration.fixed)
        parents = declaration.is_ if declaration is not None else ()
        for parent in parents:
            value = fixed_for_kind(parent, (*seen, kind_id))
            if value is not None:
                return value
        return base_fixed.get(kind_id)

    return fixed_for_kind(entity.kind)


def _placement_rows(package: Any, item_id: str) -> list[dict[str, Any]]:
    entities = _entities(package)
    rows = []
    for scene in package.scenes:
        placement = scene.metadata.item_placements.get(item_id)
        if placement is None:
            continue
        if isinstance(placement, str):
            rows.append(
                {
                    "scene_id": scene.metadata.scene_id,
                    "parent_id": placement,
                    "parent_name": getattr(entities.get(placement), "name", placement),
                    "relation": "placement",
                    "fixed": _effective_fixed(package, placement),
                }
            )
            continue
        parent_id = placement.parent
        relation = "under" if placement.under else "part_of" if placement.part_of else "in"
        rows.append(
            {
                "scene_id": scene.metadata.scene_id,
                "parent_id": parent_id,
                "parent_name": getattr(entities.get(parent_id), "name", parent_id),
                "relation": relation,
                "fixed": _effective_fixed(package, parent_id),
            }
        )
    return rows


def _asserts_fact(operation: Any, fact_id: str) -> bool:
    return operation.op == "assert" and operation.fact_id == fact_id and operation.value is not False


def _knowledge_sources(package: Any, fact_id: str) -> list[Any]:
    return [
        entry
        for entry in package.knowledge.knowledge
        if any(_asserts_fact(operation, fact_id) for operation in entry.establishes)
    ]


def _handoff_sources(package: Any, fact_id: str) -> list[Any]:
    return [delivery for delivery in package.deliveries if delivery.fact_id == fact_id]


def _deadline_sources(package: Any, fact_id: str) -> list[Any]:
    return [
        event
        for event in package.pacing.events
        if any(effect.fact_id == fact_id and effect.equals is not False for effect in event.effects)
    ]


def _knowledge_row(entry: Any, parent_id: str | None) -> dict[str, Any]:
    return {
        "id": entry.id,
        "scene_ids": list(entry.available_in_scenes),
        "earn_when": entry.earn_when,
        "delivery_text": entry.delivery_text,
        "voiceable": bool(entry.voiceable),
        "leak_terms": list(entry.leak_terms or ()),
        "search": bool(set(entry.reach_entity_ids) or set(entry.action_evidence)),
    }


def _handoff_row(delivery: Any) -> dict[str, Any]:
    return {
        "id": delivery.fact_id,
        "scene_id": delivery.scene_id,
        "text": delivery.fallback_text,
        "cue_text": delivery.cue_text,
        "voiceable": None,
    }


def _deadline_row(event: Any) -> dict[str, Any]:
    texts = [realization.text for realization in event.realizations]
    return {
        "id": event.id,
        "scene_id": event.scene_id,
        "text": texts,
        "voiceable": None,
    }


def _reveal_path(package: Any, item_id: str, parent_id: str | None) -> tuple[dict[str, Any], ...]:
    facts = []
    for fact_id, effects in package.world.fact_effects.items():
        matching_effects = [
            "reveal" if effect.reveal == item_id else "move"
            for effect in effects
            if effect.reveal == item_id or effect.move == item_id
        ]
        if not matching_effects:
            continue
        knowledge = _knowledge_sources(package, fact_id)
        facts.append(
            {
                "fact_id": fact_id,
                "effects": matching_effects,
                "knowledge": [_knowledge_row(entry, parent_id) for entry in knowledge],
                "handoffs": [_handoff_row(delivery) for delivery in _handoff_sources(package, fact_id)],
                "deadlines": [_deadline_row(event) for event in _deadline_sources(package, fact_id)],
            }
        )
    return tuple(facts)


def _is_search_source(fact: dict[str, Any]) -> bool:
    return any(source["search"] for source in fact["knowledge"])


def _has_reaching_knowledge(package: Any, path: tuple[dict[str, Any], ...], parent_id: str) -> bool:
    return any(
        parent_id in entry.reach_entity_ids for fact in path for entry in _knowledge_sources(package, fact["fact_id"])
    )


def _has_knowledge(path: tuple[dict[str, Any], ...]) -> bool:
    return any(fact["knowledge"] for fact in path)


def _is_character_parent(package: Any, parent_id: str | None) -> bool:
    return parent_id in {npc.id for npc in package.world.npcs}


def _earn_kind(
    package: Any,
    placements: list[dict[str, Any]],
    path: tuple[dict[str, Any], ...],
) -> str:
    placement = placements[0] if placements else None
    parent_id = placement["parent_id"] if placement else None
    if _is_character_parent(package, parent_id):
        return "given_by_character"
    if (
        placement
        and placement["relation"] == "under"
        and parent_id is not None
        and _has_reaching_knowledge(package, path, parent_id)
    ):
        return "search"
    if placement and placement["relation"] != "under" and _has_knowledge(path):
        return "action_result"
    if any(fact["handoffs"] for fact in path):
        return "handoff_only"
    return "unreached"


def _source_texts(path: tuple[dict[str, Any], ...]) -> list[str]:
    texts = []
    for fact in path:
        for source in fact["knowledge"]:
            if source["delivery_text"]:
                texts.append(source["delivery_text"])
        for source in fact["handoffs"]:
            texts.append(source["text"])
        for source in fact["deadlines"]:
            texts.extend(source["text"])
    return texts


def _name_in_text(text: str | None, forms: tuple[str, ...]) -> bool:
    if not text:
        return False
    folded = text.casefold()
    return any(form.casefold() in folded for form in forms)


def _scene_order(package: Any) -> tuple[str, ...]:
    route = tuple(package.storylet_routes.canonical_scene_chain)
    return (*route, *(scene.metadata.scene_id for scene in package.scenes if scene.metadata.scene_id not in route))


def _scene_texts(scene: Any) -> tuple[tuple[str, str], ...]:
    metadata = scene.metadata
    texts: list[tuple[str, str]] = [("entry", metadata.entry_text)]
    texts.extend(("entry_variant", variant.text) for variant in metadata.entry_variants)
    texts.extend(("beat", beat.prose) for beat in scene.beats.values())
    texts.extend(("details", detail) for beat in scene.beats.values() for detail in beat.details)
    return tuple(texts)


def _earning_scene_ids(path: tuple[dict[str, Any], ...]) -> set[str]:
    scene_ids = set()
    for fact in path:
        for source in fact["knowledge"]:
            scene_ids.update(source["scene_ids"])
        scene_ids.update(source["scene_id"] for source in fact["handoffs"])
        scene_ids.update(source["scene_id"] for source in fact["deadlines"])
    return scene_ids


def _public_mentions(package: Any, forms: tuple[str, ...], path: tuple[dict[str, Any], ...]) -> list[dict[str, str]]:
    order = _scene_order(package)
    earning_scenes = _earning_scene_ids(path)
    if not earning_scenes:
        return []
    earning_indexes = [order.index(scene_id) for scene_id in earning_scenes if scene_id in order]
    if not earning_indexes:
        return []
    last_scene = max(earning_indexes)
    mentions = []
    for scene_id in order[: last_scene + 1]:
        scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
        for source, text in _scene_texts(scene):
            if _name_in_text(text, forms):
                mentions.append({"scene_id": scene_id, "source": source, "text": text})
    return mentions


def _pointer(package: Any, parent_id: str | None, path: tuple[dict[str, Any], ...]) -> str:
    if parent_id is None:
        return "none"
    reveal_facts = {fact["fact_id"] for fact in path}
    earning_scenes = _earning_scene_ids(path)
    reveal_entries = {source["id"] for fact in path for source in fact["knowledge"]}
    candidates = []
    for entry in package.knowledge.knowledge:
        if entry.id in reveal_entries or not entry.repeatable or entry.audience.kind != "public":
            continue
        if not (set(entry.entity_ids) | set(entry.reach_entity_ids)) & {parent_id}:
            continue
        if not any(predicate.fact_id in reveal_facts and predicate.equals is False for predicate in entry.requires):
            continue
        scenes = earning_scenes & set(entry.available_in_scenes)
        candidates.extend((scene_id, entry.id) for scene_id in scenes)
    if not candidates:
        return "none"
    order = _scene_order(package)
    candidates.sort(key=lambda item: (order.index(item[0]) if item[0] in order else len(order), item[1]))
    return candidates[0][1]


def _downstream(package: Any, reveal_facts: set[str]) -> dict[str, list[str]]:
    knowledge = sorted(
        entry.id
        for entry in package.knowledge.knowledge
        if any(predicate.fact_id in reveal_facts for predicate in entry.requires)
    )
    storylets = sorted(
        storylet.id
        for storylet in package.storylet_routes.storylets
        if any(predicate.fact_id in reveal_facts for predicate in storylet.activation_conditions)
    )
    handoffs = sorted(
        delivery.fact_id
        for delivery in package.deliveries
        if any(
            getattr(requirement, "fact_id", None) in reveal_facts for requirement in getattr(delivery, "requires", ())
        )
    )
    return {"knowledge": knowledge, "storylets": storylets, "handoffs": handoffs}


def _item_row(package: Any, item: Any) -> dict[str, Any]:
    forms = _forms(item)
    placements = _placement_rows(package, item.id)
    parent_id = placements[0]["parent_id"] if placements else None
    path = _reveal_path(package, item.id, parent_id)
    earn_kind = _earn_kind(package, placements, path)
    delivery_texts = _source_texts(path)
    leak_terms = [term for fact in path for entry in fact["knowledge"] for term in entry["leak_terms"]]
    reveal_facts = {fact["fact_id"] for fact in path}
    return {
        "id": item.id,
        "display_name": item.name,
        "aliases": list(item.aliases),
        "scoped_aliases": list(item.scoped_aliases),
        "placements": placements,
        "reveal_path": {"facts": list(path)},
        "earn_kind": earn_kind,
        "delivery_names_item": (
            "n/a" if not delivery_texts else any(_name_in_text(text, forms) for text in delivery_texts)
        ),
        "leak_terms_cover_name": any(_name_in_text(term, forms) for term in leak_terms),
        "has_disclosure_guard": any(guard.unlock_fact in reveal_facts for guard in package.world.disclosure_guards),
        "pointer": _pointer(package, parent_id, path),
        "public_mentions_before_reveal": _public_mentions(package, forms, path),
        "downstream": _downstream(package, reveal_facts),
    }


def audit_package(package: Any) -> dict[str, Any]:
    return {
        "story_id": package.story_id,
        "items": [_item_row(package, item) for item in package.world.items if item.hidden],
    }


def _markdown(data: dict[str, Any]) -> str:
    rows = data["items"]
    lines = [
        "# Hidden thing audit",
        "",
        f"Story: `{data['story_id']}`. Hidden items: {len(rows)}.",
        "",
        "## Summary",
        "",
        "| ID | Earn kind | Delivery names item | Leak terms cover name | Disclosure guard | Pointer | "
        "Public mentions before reveal |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        mentions = len(row["public_mentions_before_reveal"])
        lines.append(
            f"| {row['id']} | {row['earn_kind']} | {_yes_no(row['delivery_names_item'])} | "
            f"{_yes_no(row['leak_terms_cover_name'])} | {_yes_no(row['has_disclosure_guard'])} | "
            f"{row['pointer']} | {mentions} |"
        )
    lines.extend(
        [
            "",
            "Legend: `search` = under a parent reached by knowledge; `given_by_character` = placed in an NPC; "
            "`action_result` = non-character placement revealed by knowledge; `handoff_only` = only a handoff "
            "delivery asserts the fact; `unreached` = no typed earning path.",
        ]
    )
    lines.extend(["", "## Details", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['display_name']} (`{row['id']}`)",
                "",
                f"Aliases: {_join(row['aliases'])}. Scoped aliases: {_join(row['scoped_aliases'])}.",
                "",
                "#### Declared placement",
                "",
                "| Scene | Parent | Relation | Parent fixed |",
                "| --- | --- | --- | --- |",
            ]
        )
        if row["placements"]:
            lines.extend(
                f"| {placement['scene_id']} | {placement['parent_name'] or placement['parent_id'] or 'none'} | "
                f"{placement['relation']} | {_yes_no(placement['fixed'])} |"
                for placement in row["placements"]
            )
        else:
            lines.append("| none | none | none | n/a |")
        lines.extend(["", "#### Reveal path", ""])
        if not row["reveal_path"]["facts"]:
            lines.append("No authored fact effect reveals or moves this item.")
        for fact in row["reveal_path"]["facts"]:
            lines.append(f"- Fact `{fact['fact_id']}` ({', '.join(fact['effects'])}).")
            for source in fact["knowledge"]:
                lines.append(
                    f"  - Knowledge `{source['id']}`: earn when `{source['earn_when'] or 'n/a'}`; "
                    f"voiceable `{source['voiceable']}`; delivery: {source['delivery_text'] or 'n/a'}"
                )
            for source in fact["handoffs"]:
                lines.append(f"  - Handoff `{source['id']}`: {source['text']}")
            for source in fact["deadlines"]:
                lines.append(f"  - Pacing deadline `{source['id']}`: {' '.join(source['text']) or 'n/a'}")
        lines.extend(
            [
                "",
                f"Earn kind: `{row['earn_kind']}`. Delivery names item: `{row['delivery_names_item']}`.",
                f"Leak terms cover name: `{row['leak_terms_cover_name']}`. "
                f"Disclosure guard: `{row['has_disclosure_guard']}`.",
                f"Pointer: `{row['pointer']}`.",
                "",
                "#### Public mentions before reveal",
                "",
            ]
        )
        if row["public_mentions_before_reveal"]:
            lines.extend(
                f"- `{mention['scene_id']}` ({mention['source']}): {mention['text']}"
                for mention in row["public_mentions_before_reveal"]
            )
        else:
            lines.append("None.")
        downstream = row["downstream"]
        lines.extend(
            [
                "",
                "#### Downstream",
                "",
                f"Knowledge: {_join(downstream['knowledge'])}. Storylets: {_join(downstream['storylets'])}. "
                f"Handoffs: {_join(downstream['handoffs'])}.",
                "",
            ]
        )
    lines.extend(
        [
            "## Not checked",
            "",
            "This audit reads authored package files only and proves nothing about narration.",
            "",
        ]
    )
    return "\n".join(lines)


def _join(values: list[str] | tuple[str, ...]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "none"


def _yes_no(value: Any) -> str:
    if value == "n/a" or value is None:
        return "n/a"
    return "yes" if value else "no"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit hidden things in a story package.")
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        package = load_story_package(args.package_dir)
    except (OSError, StoryPackageError, ValueError) as exc:
        print(f"Could not load story package: {exc}", file=sys.stderr)
        return 2
    data = audit_package(package)
    output = json.dumps(data, indent=2, sort_keys=True) + "\n" if args.as_json else _markdown(data)
    if args.out is not None:
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
