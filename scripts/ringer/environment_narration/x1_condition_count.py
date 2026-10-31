"""Offline count of undeclared typed condition proposals in the drain corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DETAILS_ROOT = ROOT / "bench" / "results" / "environment-narration" / "t9h-drain-details"
PACKAGE_ROOT = ROOT / "data" / "stories" / "continuity-initiative"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _world():
    from storygame.runtime.state import RuntimeState
    from storygame.runtime.world_model import world_for
    from storygame.story_package.loader import load_story_package

    package = load_story_package(PACKAGE_ROOT)
    state = RuntimeState.bootstrap(package)
    return world_for(package, state.facts)


def declared_values(world: Any, name: str) -> set[str]:
    """Return canonical poles and aliases declared for a named world thing."""

    entity_id = world.resolve(name)
    if entity_id is None:
        return set()
    values: set[str] = set()
    for definition in world.axis_definitions(entity_id):
        values.update(str(value).casefold() for value in definition.get("poles", ()))
        aliases = definition.get("aliases", {})
        if isinstance(aliases, dict):
            values.update(str(alias).casefold() for alias in aliases)
    return values


def _condition_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def _condition_info(item_facts: Any, world: Any) -> tuple[bool, bool]:
    if not isinstance(item_facts, dict):
        return False, False
    with_condition = False
    with_undeclared_condition = False
    for name, facts in item_facts.items():
        if not isinstance(facts, dict) or "condition" not in facts:
            continue
        values = _condition_values(facts["condition"])
        if not values:
            continue
        declared = declared_values(world, str(name))
        entity_id = world.resolve(str(name))
        if entity_id is None or any(value.casefold() not in declared for value in values):
            with_condition = True
        if entity_id is None or any(value.casefold() not in declared for value in values):
            with_undeclared_condition = True
    return with_condition, with_undeclared_condition


def _row_labels(stage: str, details_root: Path = DETAILS_ROOT) -> dict[int, dict[str, Any]]:
    stage_root = details_root / stage
    sheet = stage_root / ("sheet.md" if stage == "screen" else "sheet")
    key = _read_json(sheet / "blind_key.json")
    labels = _read_json(sheet / "labels.json")
    return {int(entry["row_index"]): labels[opaque_id] for opaque_id, entry in key.items()}


def _rows(stage: str, details_root: Path = DETAILS_ROOT) -> list[dict[str, Any]]:
    document = _read_json(details_root / stage / "rows.json")
    labels = _row_labels(stage, details_root)
    rows = []
    for row_index, row in enumerate(document["rows"], start=1):
        response = json.loads(row["response_text"])
        label = labels[row_index]
        forbidden = bool(label.get("invents_ajar_or_cover_state") or label.get("asserts_definite_contents"))
        if label.get("invents_ajar_or_cover_state"):
            kind = "ajar_or_cover"
        elif label.get("asserts_definite_contents"):
            kind = "contents"
        else:
            kind = None
        rows.append(
            {
                "id": f"{stage}-{row_index:03d}",
                "forbidden": forbidden,
                "kind": kind,
                "item_facts": response.get("item_facts", {}),
            }
        )
    return rows


def _count(details_root: Path = DETAILS_ROOT) -> dict[str, Any]:
    world = _world()
    rows = _rows("screen", details_root) + _rows("confirm", details_root)
    forbidden_rows = [row for row in rows if row["forbidden"]]
    clean_rows = [row for row in rows if not row["forbidden"]]
    annotated = []
    for row in rows:
        raw, undeclared = _condition_info(row["item_facts"], world)
        annotated.append({**row, "with_condition": raw, "with_undeclared_condition": undeclared})

    def ids(items: list[dict[str, Any]]) -> list[str]:
        return [item["id"] for item in items]

    forbidden_annotated = [row for row in annotated if row["forbidden"]]
    clean_annotated = [row for row in annotated if not row["forbidden"]]
    breakdown = {}
    for kind in ("ajar_or_cover", "contents"):
        kind_rows = [row for row in forbidden_annotated if row["kind"] == kind]
        breakdown[kind] = {
            "labeled": len(kind_rows),
            "with_condition": sum(row["with_condition"] for row in kind_rows),
            "with_undeclared_condition": sum(row["with_undeclared_condition"] for row in kind_rows),
            "ids": ids(kind_rows),
            "with_condition_ids": ids([row for row in kind_rows if row["with_condition"]]),
            "with_undeclared_condition_ids": ids([row for row in kind_rows if row["with_undeclared_condition"]]),
        }

    forbidden_with_condition = sum(row["with_condition"] for row in forbidden_annotated)
    clean_with_condition = sum(row["with_condition"] for row in clean_annotated)
    forbidden_with_undeclared = sum(row["with_undeclared_condition"] for row in forbidden_annotated)
    clean_with_undeclared = sum(row["with_undeclared_condition"] for row in clean_annotated)
    return {
        "labeled_forbidden": len(forbidden_rows),
        "labeled_clean": len(clean_rows),
        "forbidden_with_condition": forbidden_with_condition,
        "clean_with_condition": clean_with_condition,
        "forbidden_with_undeclared_condition": forbidden_with_undeclared,
        "clean_with_undeclared_condition": clean_with_undeclared,
        "forbidden_undeclared_equals_raw": forbidden_with_undeclared == forbidden_with_condition,
        "clean_undeclared_equals_raw": clean_with_undeclared == clean_with_condition,
        "undeclared_equals_raw": {
            "forbidden": forbidden_with_undeclared == forbidden_with_condition,
            "clean": clean_with_undeclared == clean_with_condition,
        },
        "forbidden_ids": ids(forbidden_annotated),
        "clean_ids": ids(clean_annotated),
        "forbidden_with_condition_ids": ids([row for row in forbidden_annotated if row["with_condition"]]),
        "clean_with_condition_ids": ids([row for row in clean_annotated if row["with_condition"]]),
        "forbidden_with_undeclared_condition_ids": ids(
            [row for row in forbidden_annotated if row["with_undeclared_condition"]]
        ),
        "clean_with_undeclared_condition_ids": ids(
            [row for row in clean_annotated if row["with_undeclared_condition"]]
        ),
        "breakdown": breakdown,
        "forbidden_kind_breakdown": breakdown,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-build-only", action="store_true", required=True)
    parser.add_argument("--details-root", type=Path, default=DETAILS_ROOT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = _count(args.details_root)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "x1_count.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "x1: "
        f"forbidden={result['labeled_forbidden']} clean={result['labeled_clean']} "
        f"raw={result['forbidden_with_condition']}/{result['clean_with_condition']} "
        f"undeclared={result['forbidden_with_undeclared_condition']}/{result['clean_with_undeclared_condition']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
