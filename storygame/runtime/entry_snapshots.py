"""Versioned, deterministic scene-entry snapshots for loaded story packages."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from worldkeeper import diff_states

from storygame.runtime.entry_seed import _advance_state_to_scene
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import CueStage, RuntimeState, TurnDelivery
from storygame.runtime.world_model import world_for
from storygame.story_package.dependencies import consumers, producers
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import StoryPackage
from storygame.web_demo import _default_package_root


class EntrySnapshotError(ValueError):
    """Raised when an entry snapshot cannot be trusted or resumed."""


_OMITTED_RUNTIME_FIELDS = (
    "turn_records",
    "pending_break",
    "pending_snapshot",
    "pending_proposal",
    "pending_capture",
    "last_turn_delivery",
)


def _scene(package: StoryPackage, scene_id: str):
    try:
        return next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    except StopIteration as error:
        raise EntrySnapshotError(f"scene {scene_id} is not in package {package.story_id}") from error


def _source_fingerprint(story_root: Path) -> str:
    """Hash package files while excluding the generated entry directory."""

    digest = hashlib.sha256()
    for path in sorted(path for path in story_root.rglob("*") if path.is_file()):
        relative = path.relative_to(story_root)
        if relative.parts and relative.parts[0] == "entry":
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _package_root(package: StoryPackage) -> Path:
    """Find the source package used to load ``package`` for fingerprint checks."""

    try:
        from storygame.story_source.lookup import _source_trees

        trees = _source_trees(package)
    except (ImportError, OSError):
        trees = ()
    if trees:
        source_root = trees[0].root.resolve()
        return source_root.parent if source_root.name == "source" else source_root
    candidate = Path.cwd() / "data" / "stories" / package.story_id
    if candidate.is_dir():
        return candidate
    raise EntrySnapshotError(f"cannot determine the source root for package {package.story_id}")


def _fact_row(fact: Fact) -> dict[str, str | None]:
    return {
        "predicate": fact.predicate,
        "subject": fact.subject,
        "object": fact.object,
        "value": fact.value,
    }


def _fact_sort_key(row: Mapping[str, Any]) -> tuple[tuple[int, str], ...]:
    return tuple(
        (0, "") if row.get(field) is None else (1, str(row[field]))
        for field in ("predicate", "subject", "object", "value")
    )


def _entry_defaults(state: RuntimeState, scene_id: str) -> None:
    """Fail closed if a scene entry carries turn-local or break-local state."""

    problems = []
    if state.turn_records:
        problems.append("turn_records is not at its default")
    if state.pending_break is not None:
        problems.append("pending_break is not at its default")
    if state.pending_snapshot is not None:
        problems.append("pending_snapshot is not at its default")
    if state.pending_proposal is not None:
        problems.append("pending_proposal is not at its default")
    if state.pending_capture is not None:
        problems.append("pending_capture is not at its default")
    if state.last_turn_delivery != TurnDelivery():
        problems.append("last_turn_delivery is not at its default")
    if problems:
        raise EntrySnapshotError(f"scene {scene_id} entry invariant: {', '.join(problems)}")


def _normalize_scene_entry(state: RuntimeState) -> None:
    """Start each canonical visit with only state that can cross a scene boundary."""

    if any(getattr(state, field) is not None for field in _OMITTED_RUNTIME_FIELDS[1:5]):
        raise EntrySnapshotError(f"scene {state.current_scene_id} canonical path has pending transient state")
    state.turn_records.clear()
    state.last_turn_delivery = TurnDelivery()
    _entry_defaults(state, state.current_scene_id)


def _canonical_entries(package: StoryPackage) -> list[tuple[RuntimeState, dict[str, object]]]:
    state = RuntimeState.bootstrap(package)
    _entry_defaults(state, state.current_scene_id)
    entries: list[tuple[RuntimeState, dict[str, object]]] = [(copy.deepcopy(state), {"turns": 0, "storylets": []})]
    total_turns = 0
    delivered: list[str] = []
    for scene in package.scenes[1:]:
        reached, turns = _advance_state_to_scene(package, state, scene.metadata.scene_id, "canonical")
        if not reached:
            raise EntrySnapshotError(f"canonical path did not reach scene {scene.metadata.scene_id}")
        total_turns += len(turns)
        for turn in turns:
            for storylet_id in turn["storylets_delivered"]:
                if storylet_id not in delivered:
                    delivered.append(storylet_id)
        _normalize_scene_entry(state)
        entries.append(
            (
                copy.deepcopy(state),
                {"turns": total_turns, "storylets": list(delivered)},
            )
        )
    return entries


def _snapshot_for_state(
    package: StoryPackage,
    story_root: Path,
    state: RuntimeState,
    path: Mapping[str, object],
) -> dict[str, object]:
    _entry_defaults(state, state.current_scene_id)
    world = world_for(package, state.facts)
    story_facts = sorted(
        (_fact_row(fact) for fact in state.facts.asserted if not fact.predicate.startswith("wk_")),
        key=_fact_sort_key,
    )
    runtime = {
        "current_scene_id": state.current_scene_id,
        "phase": state.phase,
        "turn_index": state.turn_index,
        "scene_entered_at_turn": state.scene_entered_at_turn,
        "active_event_ids": sorted(state.active_event_ids),
        "fired_event_ids": sorted(state.fired_event_ids),
        "delivered_cue_ids": list(state.delivered_cue_ids),
        "cue_stages": [stage.model_dump(mode="json") for stage in state.cue_stages],
        "staged_cue_fact_id": state.staged_cue_fact_id,
        "staged_cue_stage": state.staged_cue_stage,
        "staged_handoff_fact_ids": sorted(state.staged_handoff_fact_ids),
        "story_complete": state.story_complete,
    }
    return {
        "schema": 1,
        "story_id": package.story_id,
        "scene_id": state.current_scene_id,
        "source_fingerprint": _source_fingerprint(story_root),
        "path": {
            "persona": "canonical",
            "turns": path["turns"],
            "storylets_delivered": path["storylets"],
        },
        "world": world.export_state(),
        "story_facts": story_facts,
        "runtime": runtime,
    }


def build_entry_snapshot(package: StoryPackage, story_root: Path, scene_id: str) -> dict[str, object]:
    """Build the canonical golden snapshot for one scene."""

    _scene(package, scene_id)
    for state, path in _canonical_entries(package):
        if state.current_scene_id == scene_id:
            return _snapshot_for_state(package, Path(story_root), state, path)
    raise EntrySnapshotError(f"canonical path did not produce scene {scene_id}")


def _snapshot_path(story_root: Path, scene_id: str) -> Path:
    return Path(story_root) / "entry" / f"{scene_id}.json"


def write_entry_snapshots(story_root: Path) -> list[Path]:
    """Regenerate all default-package entry files and return their paths."""

    story_root = Path(story_root)
    package = load_story_package(story_root)
    fingerprint = _source_fingerprint(story_root)
    entry_dir = story_root / "entry"
    entry_dir.mkdir(exist_ok=True)
    paths: list[Path] = []
    for state, path in _canonical_entries(package):
        snapshot = _snapshot_for_state(package, story_root, state, path)
        assert snapshot["source_fingerprint"] == fingerprint
        destination = _snapshot_path(story_root, state.current_scene_id)
        destination.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths.append(destination)
    return paths


def load_entry_snapshot(story_root: Path, scene_id: str) -> dict[str, object]:
    """Load one JSON snapshot without silently accepting malformed data."""

    path = _snapshot_path(Path(story_root), scene_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EntrySnapshotError(f"cannot load entry snapshot {path}: {error}") from error
    if not isinstance(value, dict):
        raise EntrySnapshotError(f"entry snapshot {path} must be a JSON object")
    return value


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EntrySnapshotError(f"snapshot {name} must be an object")
    return value


def _package_fingerprint(package: StoryPackage) -> str:
    return _source_fingerprint(_package_root(package))


def state_from_snapshot(package: StoryPackage, snapshot: dict[str, object]) -> RuntimeState:
    """Rebuild a runtime state from a trusted, package-matching snapshot."""

    if not isinstance(snapshot, dict):
        raise EntrySnapshotError("entry snapshot must be an object")
    if snapshot.get("schema") != 1:
        raise EntrySnapshotError("unknown entry snapshot schema")
    if snapshot.get("story_id") != package.story_id:
        raise EntrySnapshotError("entry snapshot story_id does not match the loaded package")
    scene_id = snapshot.get("scene_id")
    if not isinstance(scene_id, str):
        raise EntrySnapshotError("entry snapshot scene_id is missing")
    scene = _scene(package, scene_id)
    try:
        expected_fingerprint = _package_fingerprint(package)
    except EntrySnapshotError:
        raise
    if snapshot.get("source_fingerprint") != expected_fingerprint:
        raise EntrySnapshotError("entry snapshot source_fingerprint does not match the loaded package")

    story_rows = snapshot.get("story_facts")
    if not isinstance(story_rows, list):
        raise EntrySnapshotError("snapshot story_facts must be a list")
    facts: list[Fact] = []
    for row in story_rows:
        item = _require_mapping(row, "story_facts entry")
        try:
            fact = Fact.model_validate(dict(item))
        except ValueError as error:
            raise EntrySnapshotError(f"invalid story fact: {error}") from error
        if fact.predicate.startswith("wk_"):
            raise EntrySnapshotError("story_facts may not contain worldkeeper facts")
        facts.append(fact)

    runtime = _require_mapping(snapshot.get("runtime"), "runtime")
    try:
        state = RuntimeState(
            package=package,
            current_scene_id=runtime["current_scene_id"],
            phase=runtime["phase"],
            turn_index=runtime["turn_index"],
            scene_entered_at_turn=runtime["scene_entered_at_turn"],
            active_event_ids=set(runtime["active_event_ids"]),
            fired_event_ids=set(runtime["fired_event_ids"]),
            delivered_cue_ids=tuple(runtime["delivered_cue_ids"]),
            cue_stages=tuple(CueStage.model_validate(item) for item in runtime["cue_stages"]),
            staged_cue_fact_id=runtime["staged_cue_fact_id"],
            staged_cue_stage=runtime["staged_cue_stage"],
            staged_handoff_fact_ids=tuple(runtime["staged_handoff_fact_ids"]),
            story_complete=runtime["story_complete"],
            facts=FactStore(asserted=facts),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise EntrySnapshotError(f"invalid runtime state in scene {scene_id}: {error}") from error
    if state.current_scene_id != scene_id:
        raise EntrySnapshotError("snapshot scene_id does not match runtime current_scene_id")

    world_data = _require_mapping(snapshot.get("world"), "world")
    result = world_for(package, state.facts).import_state(dict(world_data))
    if not result.ok:
        raise EntrySnapshotError(f"invalid world state in scene {scene_id}: {result.reason}")
    _entry_defaults(state, scene_id)
    world = world_for(package, state.facts)
    # Some authored scenes name a room while the canonical placement names a
    # sibling sub-location.  Validate the actual world location at the entry
    # boundary; changing that placement here would make the snapshot diverge
    # from the canonical path's world state.
    location_id = world.area(package.world.protagonist_id) or scene.metadata.location_id
    problems = world.entry_problems(package.world.protagonist_id, location_id)
    if problems:
        raise EntrySnapshotError(f"scene {scene_id} entry invariant problems: {'; '.join(problems)}")
    return state


def _snapshot_map(snapshots: object) -> dict[str, dict[str, object]]:
    if isinstance(snapshots, Mapping):
        return {str(scene_id): value for scene_id, value in snapshots.items() if isinstance(value, dict)}
    if isinstance(snapshots, Iterable) and not isinstance(snapshots, (str, bytes)):
        result = {}
        for value in snapshots:
            if isinstance(value, dict) and isinstance(value.get("scene_id"), str):
                result[value["scene_id"]] = value
        return result
    raise EntrySnapshotError("snapshots must be a scene mapping or iterable of snapshot objects")


def _snapshot_supplies(snapshot: Mapping[str, object], fact_id: str) -> bool:
    return any(
        isinstance(row, Mapping)
        and row.get("predicate") == fact_id
        and str(row.get("value", row.get("object"))).lower() == "true"
        for row in snapshot.get("story_facts", ())
    )


def carry_in_report(package: StoryPackage, snapshots: object) -> list[dict[str, object]]:
    """Report facts that earlier routes must carry into each scene consumer."""

    snapshot_by_scene = _snapshot_map(snapshots)
    scene_order = {scene.metadata.scene_id: index for index, scene in enumerate(package.scenes)}
    fact_ids = sorted({fact.id for fact in package.knowledge.facts} | set(package.world.facts))
    rows: list[dict[str, object]] = []
    for fact_id in fact_ids:
        fact_producers = producers(package, fact_id)
        for consumer in consumers(package, fact_id):
            scene_id = consumer.scene_id
            if scene_id is None or scene_id not in scene_order or not fact_producers:
                continue
            scene_index = scene_order[scene_id]
            if not all(
                (producer.kind == "claim" and producer.scene_id is None)
                or (producer.scene_id is not None and scene_order.get(producer.scene_id, scene_index) < scene_index)
                for producer in fact_producers
            ):
                continue
            rows.append(
                {
                    "scene_id": scene_id,
                    "fact_id": fact_id,
                    "consumer_kind": consumer.kind,
                    "consumer_id": consumer.record_id,
                    "supplied": _snapshot_supplies(snapshot_by_scene.get(scene_id, {}), fact_id),
                    "producer_scenes": sorted(
                        {producer.scene_id for producer in fact_producers if producer.scene_id is not None},
                        key=lambda value: scene_order.get(value, len(scene_order)),
                    ),
                }
            )
    return sorted(
        rows, key=lambda row: (scene_order[row["scene_id"]], row["fact_id"], row["consumer_kind"], row["consumer_id"])
    )


def _fact_text(row: Mapping[str, object]) -> str:
    return "/".join(
        "-" if row.get(field) is None else str(row[field]) for field in ("predicate", "subject", "object", "value")
    )


def _drift_lines(scene_id: str, actual: Mapping[str, object], expected: Mapping[str, object]) -> list[str]:
    lines = [f"DRIFT in scene {scene_id}"]
    try:
        diff = diff_states(expected["world"], actual["world"])
        for fact in diff["added"]:
            lines.append(f"world added: {_fact_text(fact)}")
        for fact in diff["removed"]:
            lines.append(f"world removed: {_fact_text(fact)}")
        for change in diff["changed"]:
            lines.append(
                f"world changed: {change['predicate']}/{change['subject']} from {change['before']} to {change['after']}"
            )
    except (KeyError, TypeError):
        lines.append("world state differs and could not be summarized")
    actual_facts = {_fact_text(row) for row in actual.get("story_facts", ()) if isinstance(row, Mapping)}
    expected_facts = {_fact_text(row) for row in expected.get("story_facts", ()) if isinstance(row, Mapping)}
    for fact in sorted(expected_facts - actual_facts):
        lines.append(f"story fact removed: {fact}")
    for fact in sorted(actual_facts - expected_facts):
        lines.append(f"story fact added: {fact}")
    if actual.get("runtime") != expected.get("runtime"):
        lines.append("runtime fields differ")
    if actual.get("path") != expected.get("path"):
        lines.append("path metadata differs")
    if len(lines) > 40:
        cut = len(lines) - 40
        lines = lines[:40] + [f"... {cut} more drift lines cut"]
    return lines


def check_entry_snapshots(story_root: Path) -> list[str]:
    """Return plain-language problems with all committed entry snapshots."""

    story_root = Path(story_root)
    package = load_story_package(story_root)
    expected_by_scene = {
        state.current_scene_id: _snapshot_for_state(package, story_root, state, path)
        for state, path in _canonical_entries(package)
    }
    fingerprint = _source_fingerprint(story_root)
    loaded: dict[str, dict[str, object]] = {}
    problems: list[str] = []
    for scene in package.scenes:
        scene_id = scene.metadata.scene_id
        path = _snapshot_path(story_root, scene_id)
        if not path.is_file():
            problems.append(f"missing entry snapshot: {path}")
            continue
        try:
            snapshot = load_entry_snapshot(story_root, scene_id)
        except EntrySnapshotError as error:
            problems.append(str(error))
            continue
        loaded[scene_id] = snapshot
        if snapshot.get("source_fingerprint") != fingerprint:
            problems.append(f"stale fingerprint for scene {scene_id}")
        expected = expected_by_scene[scene_id]
        if snapshot != expected:
            problems.extend(_drift_lines(scene_id, snapshot, expected))
        if snapshot.get("story_id") != package.story_id:
            problems.append(f"snapshot story_id mismatch for scene {scene_id}")
        if snapshot.get("scene_id") != scene_id:
            problems.append(f"snapshot scene_id mismatch for scene {scene_id}")
        if snapshot.get("source_fingerprint") == fingerprint:
            try:
                state_from_snapshot(package, snapshot)
            except EntrySnapshotError as error:
                problems.append(f"entry invariant problem in scene {scene_id}: {error}")

    for row in carry_in_report(package, loaded.values()):
        if row["consumer_kind"] == "gate" and not row["supplied"]:
            problems.append(
                "carry-in gate problem: "
                f"scene {row['scene_id']} fact {row['fact_id']} consumer {row['consumer_id']} is not supplied"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check or write canonical story scene-entry snapshots")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "write"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--story-root", type=Path, default=_default_package_root())
    args = parser.parse_args(argv)
    if args.command == "write":
        for path in write_entry_snapshots(args.story_root):
            print(path)
        return 0
    problems = check_entry_snapshots(args.story_root)
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
