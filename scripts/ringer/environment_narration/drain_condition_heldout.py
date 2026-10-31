"""Build a deterministic non-drain held-out narration set for Step 1."""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RESULTS_ROOT = ROOT / "bench" / "results" / "environment-narration"
SHUFFLE_SEED = 880419
REAL_ROW_LIMIT = 40
WORLD_SOURCE = "data/stories/continuity-initiative/world.yaml"

SOURCE_FILES = (
    RESULTS_ROOT / "enforce-stage1" / "smoke" / "rows" / "rows.json",
    *sorted(RESULTS_ROOT.glob("shadow-sample*/full/rows/rows.json")),
    RESULTS_ROOT / "defect-probe-s1-rows.json",
    RESULTS_ROOT / "defect-probe-s2-rows.json",
    RESULTS_ROOT / "defect-probe-s3-rows.json",
)

COMMAND_THINGS = {
    "inspect the drawer": "drawer",
    "pull out the drawer": "drawer",
    "feel under the drawer": "drawer",
    "check the drawer": "drawer",
    "examine the drawer": "drawer",
    "look inside the drawer": "drawer",
    "look under the drawer": "drawer",
    "search the drawer": "drawer",
    "inspect the passenger seat": "passenger seat",
    "inspect the truck": "Kristin's truck",
    "examine the truck": "Kristin's truck",
    "enter the truck": "Kristin's truck",
    "get out of the truck": "Kristin's truck",
    "pick up my laptop": "Kristin's laptop",
    "examine my laptop": "Kristin's laptop",
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _world():
    from storygame.runtime.state import RuntimeState
    from storygame.runtime.world_model import world_for
    from storygame.story_package.loader import load_story_package

    package = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")
    state = RuntimeState.bootstrap(package)
    return world_for(package, state.facts)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _target(world: Any, name: str) -> str:
    entity_id = world.resolve(name)
    if entity_id is None:
        raise ValueError(f"held-out target is not declared by the story package: {name}")
    return world.name(entity_id)


def _recorded_world(value: Mapping[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for field in ("world_before", "before", "places_before", "world", "custody", "places"):
        recorded = value.get(field)
        if isinstance(recorded, dict):
            return field, recorded
    return None


def _open_value(value: Any) -> str | None:
    if isinstance(value, bool):
        return "open" if value else "closed"
    if isinstance(value, str) and value.casefold() in {"open", "closed"}:
        return value.casefold()
    return None


def _recorded_open_state(recorded: Mapping[str, Any], entity_id: str, world: Any) -> str | None:
    entry = recorded.get(entity_id)
    if entry is None:
        entry = recorded.get(world.name(entity_id))
    if not isinstance(entry, Mapping):
        return None
    for field in ("open_state", "open", "state"):
        state = _open_value(entry.get(field))
        if state is not None:
            return state
    axes = entry.get("axes")
    if isinstance(axes, Mapping):
        for field in ("open", "open_state"):
            state = _open_value(axes.get(field))
            if state is not None:
                return state
    return None


def _recorded_parent(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for field in ("parent", "place", "location", "held_by"):
            parent = value.get(field)
            if isinstance(parent, str):
                return parent
    return None


def _canonical_id(world: Any, value: str) -> str | None:
    if value in world.entity_ids():
        return value
    return world.resolve(value)


def _declared_contents(world: Any, entity_id: str, recorded: Mapping[str, Any]) -> list[str]:
    contents = []
    for child_id in world.contents(entity_id):
        recorded_parent = _recorded_parent(recorded.get(child_id))
        if recorded_parent is None:
            recorded_parent = _recorded_parent(recorded.get(world.name(child_id)))
        parent_id = _canonical_id(world, recorded_parent) if recorded_parent is not None else world.parent(child_id)
        if parent_id == entity_id:
            contents.append(world.name(child_id))
    return contents


def _declared_state(
    *, world: Any, thing: str, recorded: Mapping[str, Any] | None, recorded_field: str | None, source_file: str
) -> tuple[dict[str, Any] | None, str | None]:
    if recorded is None or recorded_field is None:
        return None, "no separate world or custody field is recorded for this row"

    entity_id = world.resolve(thing)
    if entity_id is None:
        return None, "the recorded target is not declared by the loaded story world"

    recorded_open = _recorded_open_state(recorded, entity_id, world)
    open_state = recorded_open
    state_source = f"{source_file}:{recorded_field}; {WORLD_SOURCE}:entity {entity_id}"
    if open_state is None:
        for definition in world.axis_definitions(entity_id):
            poles = {str(pole).casefold() for pole in definition.get("poles", ())}
            if {"open", "closed"} <= poles:
                open_state = _open_value(world.axis_values(entity_id).get(definition["name"]))
                break

    contents = _declared_contents(world, entity_id, recorded)
    hidden_contents_present = any(
        child_id in world.contents(entity_id) and world.is_hidden(child_id)
        for child_id in world.contents(entity_id)
        if world.name(child_id) in contents
    )
    notes = (
        "Recorded placements came from the turn's world field; open state and declared contents "
        "were resolved through the loaded world model."
    )
    if recorded_open is None and open_state is not None:
        notes += " The recorded field has no open axis, so the package declaration supplies that value."
    return (
        {
            "source": state_source,
            "open_state": open_state,
            "declared_contents": contents,
            "hidden_contents_present": hidden_contents_present,
            "fixed": bool(world.schema.is_fixed(entity_id)),
            "notes": notes,
        },
        None,
    )


def _legacy_capture_states(turn: Mapping[str, Any], world: Any, thing: str) -> tuple[str | None, str | None]:
    aliases = _thing_aliases(world, thing)
    engine_steps = turn.get("engine_steps")
    stages = engine_steps.get("attempt_stages", ()) if isinstance(engine_steps, Mapping) else ()
    for stage in reversed(stages if isinstance(stages, list) else ()):
        if not isinstance(stage, Mapping) or stage.get("kind") != "capture":
            continue
        request = stage.get("request")
        request_facts = request.get("item_facts_before") if isinstance(request, Mapping) else None
        reply = stage.get("reply")
        facts_after = reply.get("facts_after") if isinstance(reply, Mapping) else None
        before_facts = next(
            (request_facts[name] for name in aliases if isinstance(request_facts, Mapping) and name in request_facts),
            None,
        )
        after_facts = next(
            (facts_after[name] for name in aliases if isinstance(facts_after, Mapping) and name in facts_after),
            None,
        )

        def state_from(facts: Any) -> str | None:
            conditions = facts.get("condition") if isinstance(facts, Mapping) else None
            if not isinstance(conditions, list):
                return None
            return next((_open_value(condition) for condition in conditions), None)

        before_state = state_from(before_facts)
        after_state = state_from(after_facts)
        return before_state, after_state
    return None, None


def _turn_metadata(
    turn: Mapping[str, Any] | None,
    *,
    world: Any | None = None,
    thing: str | None = None,
    allow_legacy: bool = False,
) -> tuple[dict[str, Any], str | None]:
    if turn is None:
        return {}, "the source does not record a turn with the required command and engine fields"

    required = ("input", "engine_opened", "focus_open_state_after", "focus_open_state_committed")
    missing = [field for field in required if field not in turn]
    if missing:
        if allow_legacy and world is not None and thing is not None and "input" in turn:
            before_state, after_state = _legacy_capture_states(turn, world, thing)
            return (
                {
                    "command": turn["input"],
                    "engine_opened": before_state == "closed" and after_state == "open",
                    "open_state_after": after_state,
                    "focus_open_state_committed": after_state,
                },
                None,
            )
        fields = ", ".join(missing)
        return {}, f"the recorded turn is missing: {fields}"

    command = turn["input"]
    engine_opened = turn["engine_opened"]
    open_state_after = turn["focus_open_state_after"]
    open_state_committed = turn["focus_open_state_committed"]
    if not isinstance(command, str) or not command.strip():
        return {}, "the recorded turn has no non-empty command in input"
    if not isinstance(engine_opened, bool):
        return {}, "the recorded turn has a non-boolean engine_opened value"
    for field, value in (
        ("focus_open_state_after", open_state_after),
        ("focus_open_state_committed", open_state_committed),
    ):
        if value is not None and value not in {"open", "closed"}:
            return {}, f"the recorded turn has an invalid {field} value"
    return (
        {
            "command": command,
            "engine_opened": engine_opened,
            "open_state_after": open_state_after,
            "focus_open_state_committed": open_state_committed,
        },
        None,
    )


def _labelable_reason(declared_reason: str | None, turn_reason: str | None) -> str | None:
    reasons = []
    if declared_reason:
        reasons.append(f"declared state: {declared_reason}")
    if turn_reason:
        reasons.append(f"turn metadata: {turn_reason}")
    return "; ".join(reasons) or None


def _status(turn: dict[str, Any]) -> str:
    shadow = turn.get("observation_shadow")
    shadow = shadow if isinstance(shadow, dict) else {}
    if turn.get("error") or len(turn.get("enforce_attempts") or ()) > 1:
        return "flagged"
    if shadow.get("outcome") == "no_relations" or shadow.get("accepted") is False:
        return "flagged"
    return "ordinary"


def _real_row(
    *,
    world: Any,
    path: Path,
    source_ref: str,
    thing: str,
    narration: str,
    status: str,
    recorded: Mapping[str, Any] | None = None,
    recorded_field: str | None = None,
    turn: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    canonical_thing = _target(world, thing)
    source_file = _relative(path)
    declared_state, missing_reason = _declared_state(
        world=world,
        thing=canonical_thing,
        recorded=recorded,
        recorded_field=recorded_field,
        source_file=source_file,
    )
    metadata, metadata_reason = _turn_metadata(
        turn,
        world=world,
        thing=canonical_thing,
        allow_legacy=turn is not None,
    )
    return {
        "thing": canonical_thing,
        "source_file": source_file,
        "source": source_file,
        "source_ref": source_ref,
        "narration": narration,
        "authored": False,
        "authored_note": "",
        "declared_state": declared_state,
        "declared_state_missing_reason": missing_reason,
        "command": metadata.get("command"),
        "engine_opened": metadata.get("engine_opened"),
        "open_state_after": metadata.get("open_state_after"),
        "focus_open_state_committed": metadata.get("focus_open_state_committed"),
        "labelable": declared_state is not None and metadata_reason is None,
        "labelable_missing_reason": _labelable_reason(missing_reason, metadata_reason),
        "_status": status,
    }


def _nested_candidates(world: Any, path: Path, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for record_index, record in enumerate(data, start=1):
        for turn in record.get("turns", ()):
            command = turn.get("input")
            thing = COMMAND_THINGS.get(command)
            narration = turn.get("narration")
            if thing is None or not isinstance(narration, str) or not narration.strip():
                continue
            if not turn.get("narrator_called") and not turn.get("narration_attempts"):
                continue
            recorded_world = _recorded_world(turn)
            candidates.append(
                _real_row(
                    world=world,
                    path=path,
                    source_ref=f"record-{record_index:03d}/turn-{turn.get('turn_index', 0):03d}",
                    thing=thing,
                    narration=narration,
                    status=_status(turn),
                    recorded=recorded_world[1] if recorded_world else None,
                    recorded_field=(
                        f"turns[record-{record_index:03d}/turn-{turn.get('turn_index', 0):03d}].{recorded_world[0]}"
                        if recorded_world
                        else None
                    ),
                    turn=turn,
                )
            )
    return candidates


def _defect_candidates(world: Any, path: Path, data: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for row in data.get("rows", ()):
        context = row.get("context")
        thing = {"A": "drawer", "B": "passenger seat"}.get(str(context)[:1])
        narration = row.get("narration")
        if thing is None or not isinstance(narration, str) or not narration.strip():
            continue
        if row.get("skipped") or not row.get("usable") or row.get("status") != 200:
            continue
        recorded_world = _recorded_world(row)
        candidates.append(
            _real_row(
                world=world,
                path=path,
                source_ref=f"row-{int(row['call_index']):03d}",
                thing=thing,
                narration=narration,
                status="ordinary",
                recorded=recorded_world[1] if recorded_world else None,
                recorded_field=f"rows[{row['call_index']}].{recorded_world[0]}" if recorded_world else None,
                turn=None,
            )
        )
    return candidates


def _candidates(world: Any, source_files: tuple[Path, ...] = SOURCE_FILES) -> list[dict[str, Any]]:
    candidates = []
    for path in source_files:
        if not path.is_file():
            continue
        data = _read_json(path)
        if path.name.startswith("defect-probe-"):
            candidates.extend(_defect_candidates(world, path, data))
        else:
            records = data if isinstance(data, list) else data.get("rows", [])
            candidates.extend(_nested_candidates(world, path, records))
    return candidates


def _select_real(world: Any, source_files: tuple[Path, ...] = SOURCE_FILES) -> list[dict[str, Any]]:
    candidates = _candidates(world, source_files)
    if len(candidates) < REAL_ROW_LIMIT:
        raise ValueError(f"only {len(candidates)} usable real held-out rows were found")

    selected: list[dict[str, Any]] = []
    used: set[tuple[str, str]] = set()
    for source_file in sorted({row["source_file"] for row in candidates}):
        available = [row for row in candidates if row["source_file"] == source_file]
        preferred = next((row for row in available if row["_status"] == "flagged"), available[0])
        selected.append(preferred)
        used.add((preferred["source_file"], preferred["source_ref"]))

    target_counts = {"flagged": REAL_ROW_LIMIT // 2, "ordinary": REAL_ROW_LIMIT // 2}
    for status in ("flagged", "ordinary"):
        for row in candidates:
            key = (row["source_file"], row["source_ref"])
            if key in used or row["_status"] != status:
                continue
            if sum(item["_status"] == status for item in selected) >= target_counts[status]:
                break
            selected.append(row)
            used.add(key)

    for row in candidates:
        if len(selected) >= REAL_ROW_LIMIT:
            break
        key = (row["source_file"], row["source_ref"])
        if key not in used:
            selected.append(row)
            used.add(key)

    selected = selected[:REAL_ROW_LIMIT]
    for index, row in enumerate(selected, start=1):
        row["id"] = f"real-{index:03d}"
    return selected


def _authored_rows(real_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = ("drawer", "passenger seat", "Kristin's truck")
    bases = []
    for thing in wanted:
        base = next((row for row in real_rows if row["thing"] == thing and row["_status"] == "ordinary"), None)
        if base is None:
            raise ValueError(f"no ordinary source row available for authored {thing} cases")
        bases.append(base)

    edits = {
        "drawer": ("The drawer is ajar.", "A folded map is inside the drawer."),
        "passenger seat": ("The passenger seat is lifted.", "A flashlight is on the passenger seat."),
        "Kristin's truck": ("The truck's door is ajar.", "A red backpack is inside the truck."),
    }
    rows = []
    for base in bases:
        source = f"{base['source_file']}:{base['source_ref']}"
        variants = (
            (base["narration"], f"negative: unedited original from {source}"),
            (base["narration"] + " " + edits[base["thing"]][0], f"edit: added an ajar or lifted state to {source}"),
            (base["narration"] + " " + edits[base["thing"]][1], f"edit: added contents to {source}"),
        )
        for narration, note in variants:
            rows.append(
                {
                    "thing": base["thing"],
                    "source_file": base["source_file"],
                    "source": base["source_file"],
                    "source_ref": base["source_ref"],
                    "narration": narration,
                    "authored": True,
                    "authored_note": note,
                    "declared_state": deepcopy(base["declared_state"]),
                    "declared_state_missing_reason": base["declared_state_missing_reason"],
                    "command": base["command"],
                    "engine_opened": base["engine_opened"],
                    "open_state_after": base["open_state_after"],
                    "focus_open_state_committed": base["focus_open_state_committed"],
                    "labelable": base["labelable"],
                    "labelable_missing_reason": base["labelable_missing_reason"],
                    "_status": "ordinary",
                }
            )
    for index, row in enumerate(rows, start=1):
        row["id"] = f"authored-{index:03d}"
    return rows


def build(source_files: tuple[Path, ...] = SOURCE_FILES) -> dict[str, Any]:
    world = _world()
    real_rows = _select_real(world, source_files)
    rows = real_rows + _authored_rows(real_rows)
    for row in rows:
        row.pop("_status", None)
    return {"rows": rows}


def _surface_char(value: str) -> bool:
    return value.isalnum() or value == "_"


def _replace_surface(text: str, surface: str) -> str:
    if not surface:
        return text
    folded = text.casefold()
    wanted = surface.casefold()
    pieces = []
    cursor = 0
    while True:
        start = folded.find(wanted, cursor)
        if start < 0:
            pieces.append(text[cursor:])
            return "".join(pieces)
        end = start + len(surface)
        before_ok = start == 0 or not _surface_char(text[start - 1])
        after_ok = end == len(text) or not _surface_char(text[end])
        if before_ok and after_ok:
            pieces.extend((text[cursor:start], "[thing]"))
            cursor = end
        else:
            pieces.append(text[cursor:end])
            cursor = end


def _thing_aliases(world: Any, thing: str) -> tuple[str, ...]:
    entity_id = world.resolve(thing)
    if entity_id is None:
        return (thing,)
    entity = world.schema.entities.get(entity_id)
    name = world.name(entity_id)
    aliases = (name, *(entity.aliases if entity is not None else ()))
    head = name.rsplit(" ", 1)[-1]
    if head != name:
        aliases = (*aliases, head)
    return tuple(dict.fromkeys(sorted(aliases, key=lambda value: (-len(value), value.casefold()))))


def _blind_text(row: dict[str, Any], world: Any | None = None, surfaces: tuple[str, ...] | None = None) -> str:
    world = _world() if world is None else world
    text = row["narration"]
    surfaces = _thing_aliases(world, row["thing"]) if surfaces is None else surfaces
    for surface in surfaces:
        text = _replace_surface(text, surface)
    return text


def _blind_command(row: dict[str, Any], world: Any, surfaces: tuple[str, ...] | None = None) -> str:
    command = row["command"]
    surfaces = _thing_aliases(world, row["thing"]) if surfaces is None else surfaces
    for surface in surfaces:
        command = _replace_surface(command, surface)
    return command


def _declared_text(row: dict[str, Any]) -> str:
    state = row["declared_state"]
    open_state = state.get("open_state")
    before_text = f"the object was {open_state}" if open_state else "the object had no open/closed value"
    opened_text = "the engine opened it" if row["engine_opened"] else "the engine did not open it"
    after_state = row["open_state_after"]
    after_text = (
        f"the object was {after_state} after the turn"
        if after_state
        else "the object had no open/closed value after the turn"
    )
    contents = state.get("declared_contents")
    content_count = len(contents) if isinstance(contents, list) else 0
    hidden_text = "; some contents are hidden" if state.get("hidden_contents_present") else ""
    fixed_text = "fixed in place" if state.get("fixed") else "not fixed in place"
    return (
        f"Declared: before the turn, {before_text}; {opened_text}; {after_text}; "
        f"{content_count} declared item(s){hidden_text}; {fixed_text}."
    )


def _print_summary(rows: list[dict[str, Any]]) -> None:
    by_source: dict[str, int] = {}
    by_thing: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_source[row["source_file"]] = by_source.get(row["source_file"], 0) + 1
        by_thing.setdefault(row["thing"], []).append(row)
    print(f"heldout: {len(rows)} rows")
    for source, count in by_source.items():
        print(f"  {source}: {count}")
    print(f"labelable: {sum(row['labelable'] for row in rows)} rows")
    print("labelable by thing:")
    for thing in sorted(by_thing):
        group = by_thing[thing]
        available = sum(row["labelable"] for row in group)
        print(f"  {thing}: {available} labelable of {len(group)}")
    missing = [row for row in rows if not row["labelable"]]
    if missing:
        print("unlabelable rows:")
        for row in missing:
            print(f"  {row['id']} ({row['thing']}): {row['labelable_missing_reason']}")


def blind_sheet(heldout_path: Path, output: Path) -> None:
    document = _read_json(heldout_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("heldout file has no rows list")
    unlabelable_rows = [
        {"id": row["id"], "thing": row["thing"], "reason": row["labelable_missing_reason"]}
        for row in rows
        if row.get("labelable") is not True
    ]
    world = _world()
    surfaces = tuple(
        dict.fromkeys(
            sorted(
                (surface for row in rows for surface in _thing_aliases(world, row["thing"])),
                key=lambda value: (-len(value), value.casefold()),
            )
        )
    )
    indexed = [(index, row) for index, row in enumerate(rows, start=1) if row.get("labelable") is True]
    random.Random(SHUFFLE_SEED).shuffle(indexed)
    lines = ["# Narration sheet", ""]
    key = {}
    for position, (row_index, row) in enumerate(indexed, start=1):
        opaque_id = f"sample-{position:03d}"
        key[opaque_id] = {"row_index": row_index}
        lines.extend(
            [
                f"## {opaque_id}",
                "",
                "Narration:",
                _blind_text(row, world, surfaces),
                "",
                f"Command: {_blind_command(row, world, surfaces)}",
                _declared_text(row),
                "",
            ]
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "blind_sheet.md").write_text("\n".join(lines), encoding="utf-8")
    (output / "blind_key.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    (output / "unlabelable.json").write_text(json.dumps({"rows": unlabelable_rows}, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--blind-sheet", action="store_true")
    parser.add_argument("--heldout", type=Path)
    parser.add_argument("--source-file", action="append", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.build:
        source_files = tuple(args.source_file) if args.source_file else SOURCE_FILES
        document = build(source_files)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "heldout.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        _print_summary(document["rows"])
        return 0
    if args.heldout is None:
        parser.error("--heldout is required with --blind-sheet")
    blind_sheet(args.heldout, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
