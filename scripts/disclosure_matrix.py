"""Generate the continuity-initiative narration disclosure review."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path

from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import normalize_term

GUARD_KINDS = (
    "entity_name",
    "identifier_fragment",
    "leak_term",
    "knowledge_alias",
    "must_convey_phrase",
    "scoped_alias",
)
SCENES = tuple(f"{phase}{letter}" for phase in range(1, 4) for letter in "ABC")


def _fact_ids(item: object) -> list[str]:
    return sorted({operation.fact_id for operation in item.establishes})


def _requires(item: object) -> list[str]:
    return sorted({predicate.fact_id for predicate in item.requires})


def _available_scenes(package: object, owner_ids: tuple[str, ...], kind: str) -> list[str]:
    if kind in {"entity_name", "scoped_alias"}:
        scenes = []
        for scene in package.scenes:
            visible = NarrationSafetyValidator._scene_entity_ids(package, scene)
            if set(owner_ids) & visible:
                scenes.append(scene.metadata.scene_id)
        return scenes
    if kind == "identifier_fragment":
        return [scene.metadata.scene_id for scene in package.scenes]
    by_id = package.knowledge_indexes.by_id
    return sorted({scene for owner_id in owner_ids for scene in by_id[owner_id].available_in_scenes})


def _world_text(package: object, scene_id: str) -> str:
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    entity_ids = NarrationSafetyValidator._scene_entity_ids(package, scene)
    entities = {
        entity.id: entity
        for group in (package.world.locations, package.world.npcs, package.world.items, package.world.groups)
        for entity in group
    }
    descriptions = " ".join(
        str(value)
        for entity_id in entity_ids
        for value in entities[entity_id].model_dump().values()
        if isinstance(value, str)
    )
    return f"{scene.metadata.entry_text} {descriptions}".casefold()


def _inventory(package: object) -> list[dict[str, object]]:
    indexes = package.knowledge_indexes
    rows: dict[tuple[str, str, tuple[str, ...]], dict[str, object]] = {}

    def add(term: str, kind: str, owners: tuple[str, ...]) -> None:
        normalized = normalize_term(term)
        if not normalized:
            return
        key = (normalized, kind, tuple(sorted(owners)))
        rows[key] = {"term": normalized, "guard_kind": kind, "owner_ids": list(sorted(owners))}

    for term, owners in indexes.entity_alias_to_entities.items():
        add(term, "entity_name", tuple(owners))
    for entity in (*package.world.locations, *package.world.npcs, *package.world.items, *package.world.groups):
        for alias in entity.scoped_aliases:
            add(alias, "scoped_alias", (entity.id,))
    for term, owners in indexes.alias_to_knowledge.items():
        add(term, "knowledge_alias", tuple(owners))
    for term, owners in indexes.term_to_knowledge.items():
        if len(term.split()) > 1:
            add(term, "must_convey_phrase", tuple(owners))
    for item in package.knowledge.knowledge:
        for term in item.leak_terms or ():
            add(term, "leak_term", (item.id,))
    protected_ids = tuple(package.world.protected_knowledge)
    for term in indexes.protected_terms:
        add(term, "identifier_fragment", protected_ids)

    entries = []
    for row in rows.values():
        kind = row["guard_kind"]
        owners = tuple(row["owner_ids"])
        scenes = _available_scenes(package, owners, kind)
        row["available_scenes"] = scenes
        if kind in {"knowledge_alias", "must_convey_phrase", "leak_term"}:
            facts = sorted({fact for owner in owners for fact in _fact_ids(indexes.by_id[owner])})
            requires = sorted({fact for owner in owners for fact in _requires(indexes.by_id[owner])})
        else:
            facts = []
            requires = []
        row["unlock_fact_ids"] = facts
        row["requires"] = requires
        public_text = any(row["term"] in _world_text(package, scene_id) for scene_id in scenes)
        ordinary_entity = bool(set(indexes.entity_alias_to_entities.get(row["term"], ())))
        if (
            kind in {"knowledge_alias", "must_convey_phrase", "leak_term"}
            and facts
            and not ordinary_entity
            and not public_text
        ):
            suggestion = "secret_with_unlock_fact"
            why = "knowledge owner has establishing facts and the term is not an ordinary scene entity name"
        elif ordinary_entity or public_text:
            suggestion = "public_candidate"
            why = "term is an ordinary entity name or appears in entry/world text for an available scene"
        else:
            suggestion = "needs_review"
            why = "no public-text or knowledge-unlock rule produced a suggestion"
        row["suggested_class"] = suggestion
        row["why"] = why
        entries.append(row)
    return sorted(entries, key=lambda row: (row["term"], row["guard_kind"], row["owner_ids"]))


def _state(package: object, scene_id: str, earned_owner: str | None = None) -> RuntimeState:
    order = {scene.metadata.scene_id: index for index, scene in enumerate(package.scenes)}
    index = order[scene_id]
    scene = package.scenes[index]
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    for earlier in package.scenes[:index]:
        state._assert_scene_entry_fact(earlier.metadata.scene_id)
    if earned_owner is not None:
        item = package.knowledge_indexes.by_id.get(earned_owner)
        if item is not None:
            for operation in item.establishes:
                value = str(operation.value).lower() if isinstance(operation.value, bool) else str(operation.value)
                state.facts.assert_fact(Fact(predicate=operation.fact_id, subject="story", value=value))
    return state


def _late_state(package: object, scene_id: str, skipped_owner: str | None) -> RuntimeState:
    """Build the fixture's late-scene projection while omitting one reveal."""

    state = _state(package, scene_id)
    order = {scene.metadata.scene_id: index for index, scene in enumerate(package.scenes)}
    scene_index = order[scene_id]
    for item in package.knowledge.knowledge:
        if item.id == skipped_owner or not item.available_in_scenes:
            continue
        if not all(order[available] <= scene_index for available in item.available_in_scenes):
            continue
        for operation in item.establishes:
            if operation.op == "assert":
                value = str(operation.value).lower() if isinstance(operation.value, bool) else str(operation.value)
                state.facts.assert_fact(Fact(predicate=operation.fact_id, subject="story", value=value))
    return state


def _verdict(state: RuntimeState, term: str) -> dict[str, str]:
    proposal = ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=f"The {term} is here."),))
    candidate = copy.deepcopy(state)
    try:
        NarrationSafetyValidator().validate(state, candidate, proposal, KnowledgeProjector(), "Search the room.")
    except ProposalValidationError as error:
        return {"verdict": "rejected", "error_code": error.code or type(error).__name__}
    return {"verdict": "accepted", "error_code": ""}


def _matrix(package: object, inventory: list[dict[str, object]]) -> list[dict[str, object]]:
    states = {scene: _state(package, scene) for scene in SCENES}
    earned_states: dict[tuple[str, str | None], RuntimeState] = {}
    skipped_states: dict[tuple[str, str | None], RuntimeState] = {}
    early_verdicts: dict[tuple[str, str], dict[str, str]] = {}
    earned_verdicts: dict[tuple[str, str | None, str], dict[str, str]] = {}
    skipped_verdicts: dict[tuple[str, str | None, str], dict[str, str]] = {}
    rows = []
    for item in inventory:
        owners = tuple(item["owner_ids"])
        knowledge_owner = next((owner for owner in owners if owner in package.knowledge_indexes.by_id), None)
        for scene in SCENES:
            if scene not in item["available_scenes"]:
                continue
            term = item["term"]
            early_key = (scene, term)
            if early_key not in early_verdicts:
                early_verdicts[early_key] = _verdict(states[scene], term)
            early = early_verdicts[early_key]
            state_key = (scene, knowledge_owner)
            if state_key not in earned_states:
                earned_states[state_key] = _state(package, scene, knowledge_owner)
            if state_key not in skipped_states:
                skipped_states[state_key] = _late_state(package, scene, knowledge_owner)
            earned_key = (scene, knowledge_owner, term)
            if earned_key not in earned_verdicts:
                earned_verdicts[earned_key] = _verdict(earned_states[state_key], term)
            earned = earned_verdicts[earned_key]
            skipped_key = (scene, knowledge_owner, term)
            if skipped_key not in skipped_verdicts:
                skipped_verdicts[skipped_key] = _verdict(skipped_states[state_key], term)
            skipped = skipped_verdicts[skipped_key]
            rows.append(
                {
                    "scene": scene,
                    "term": item["term"],
                    "guard_kind": item["guard_kind"],
                    "early": early,
                    "earned": earned,
                    "skipped": skipped,
                }
            )
    return sorted(rows, key=lambda row: (row["scene"], row["term"], row["guard_kind"]))


def _markdown(data: dict[str, object]) -> str:
    inventory = data["inventory"]
    matrix = data["matrix"]
    kind_counts = Counter(row["guard_kind"] for row in inventory)
    class_counts = Counter(row["suggested_class"] for row in inventory)
    earned_rejected = [row for row in matrix if row["earned"]["verdict"] == "rejected"]
    by_key = {(item["term"], item["guard_kind"]): item for item in inventory}
    early_public = [
        row
        for row in matrix
        if row["early"]["verdict"] == "rejected"
        and by_key[(row["term"], row["guard_kind"])]["suggested_class"] == "public_candidate"
    ]
    early_secret = [
        row
        for row in matrix
        if row["early"]["verdict"] == "accepted"
        and by_key[(row["term"], row["guard_kind"])]["suggested_class"] == "secret_with_unlock_fact"
    ]

    def table(title: str, rows: list[dict[str, object]]) -> list[str]:
        lines = [f"### {title}", "", "| Scene | Term | Guard | Error |", "| --- | --- | --- | --- |"]
        lines.extend(
            f"| {row['scene']} | {row['term']} | {row['guard_kind']} | "
            f"{row['earned']['error_code'] if title.startswith('Earned') else row['early']['error_code']} |"
            for row in rows
        )
        lines.append("")
        return lines

    lines = [
        "# Disclosure vocabulary matrix",
        "",
        f"Inventory terms: {len(inventory)}. Matrix rows: {len(matrix)}.",
        "",
        "## Counts",
        "",
    ]
    lines.extend(f"- {kind}: {kind_counts[kind]}" for kind in sorted(kind_counts))
    lines.extend(["", "Suggested classes:"])
    lines.extend(f"- {kind}: {class_counts[kind]}" for kind in sorted(class_counts))
    lines.extend(
        [
            "",
            *table("Earned rejected", earned_rejected),
            *table("Early rejected public candidates", early_public),
            *table("Early accepted secret candidates", early_secret),
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path(".plans"))
    parser.add_argument("--story", default="continuity-initiative")
    args = parser.parse_args()
    package = load_story_package(Path("data/stories") / args.story)
    inventory = _inventory(package)
    data = {"inventory": inventory, "matrix": _matrix(package, inventory)}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "disclosure-matrix.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out_dir / "disclosure-matrix.md").write_text(_markdown(data), encoding="utf-8")


if __name__ == "__main__":
    main()
