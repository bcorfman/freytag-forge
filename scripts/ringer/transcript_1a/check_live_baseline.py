"""Validate transcript 1A baseline artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FIELDS = {
    "input",
    "before",
    "after",
    "places_before",
    "places_after",
    "scene",
    "turn_index",
    "selected_knowledge_ids",
    "newly_fired_event_ids",
    "reference",
    "engine_steps",
    "item_facts_unplaced",
    "prompts",
    "provider_responses",
    "narration",
    "error",
    "notes",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("replicates", type=int)
    parser.add_argument("--mode", choices=("dry", "live"), required=True)
    parser.add_argument("--turns", type=int, default=8)
    args = parser.parse_args(argv)
    errors: list[str] = []
    rows_path, summary_path = args.directory / "rows.json", args.directory / "summary.json"
    if not rows_path.is_file():
        errors.append("missing rows.json")
    if not summary_path.is_file():
        errors.append("missing summary.json")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    rows, summary = json.loads(rows_path.read_text()), json.loads(summary_path.read_text())
    if summary.get("mode") != args.mode:
        errors.append(f"summary mode is {summary.get('mode')!r}, expected {args.mode!r}")
    if args.mode == "dry":
        if len(rows) != args.replicates:
            errors.append(f"expected {args.replicates} replicates, found {len(rows)}")
        if summary.get("replicates_completed") != args.replicates:
            errors.append("dry run did not complete all replicates")
        if summary.get("real_calls", 0) != 0:
            errors.append(f"dry run made {summary.get('real_calls')} calls to real hosts")
        if summary.get("errors") != 0:
            errors.append("dry run recorded errors")
    if summary.get("calls_made", 0) > summary.get("max_calls", -1):
        errors.append("calls_made exceeds max_calls")
    recorded = 0
    for index, replicate in enumerate(rows, 1):
        turns = replicate.get("turns", [])
        recorded += len(turns)
        if args.mode == "dry" and len(turns) != args.turns:
            errors.append(f"replicate {index} has {len(turns)} turns, expected {args.turns}")
        for turn_index, turn in enumerate(turns, 1):
            missing = sorted(FIELDS - set(turn))
            if missing:
                errors.append(f"replicate {index} turn {turn_index} missing fields: {', '.join(missing)}")
            if args.mode == "dry" and turn.get("error"):
                errors.append(f"replicate {index} turn {turn_index} has error: {turn['error']}")
    if summary.get("turns_recorded") != recorded:
        errors.append("summary turns_recorded does not match rows")
    if args.mode == "live":
        print(
            f"live partial run: {len(rows)} replicates, {recorded} turns, "
            f"stopped_reason={summary.get('stopped_reason')!r}"
        )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: {len(rows)} replicates, {recorded} turns, mode={args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
