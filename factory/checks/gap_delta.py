"""Compare deterministic story gap-rule snapshots against a baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from storygame.story_package.gap_rules import run_gap_rules
from storygame.story_package.loader import load_story_package

_STORIES = Path(__file__).resolve().parents[2] / "data" / "stories"
DEFAULT_ROOT = next(path for path in sorted(_STORIES.iterdir()) if path.is_dir())


def all_anchors(root: Path) -> list[str]:
    """Return every transition and incident anchor in a story package."""

    package = load_story_package(root)
    anchors = [transition.id for transition in package.pacing.transitions]
    anchors.extend(incident.id for incident in package.incidents)
    return sorted(set(anchors))


def snapshot(root: Path, anchors: list[str] | None = None) -> dict[str, list[str]]:
    """Run all gap rules for the requested anchors and retain stable result keys."""

    selected = all_anchors(root) if anchors is None else list(anchors)
    result: dict[str, list[str]] = {}
    for anchor in sorted(set(selected)):
        try:
            results = run_gap_rules(root, anchor)
        except ValueError as exc:
            result.setdefault("__errors__", []).append(f"{anchor}|{exc}")
            continue
        result[anchor] = sorted({f"{item.rule}|{item.subject}" for item in results})
    if "__errors__" in result:
        result["__errors__"].sort()
    return result


def save_baseline(snap: dict[str, list[str]], path: Path) -> None:
    """Write a sorted JSON baseline with a trailing newline."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> dict[str, list[str]]:
    """Read a JSON gap baseline."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(anchor): [str(item) for item in values] for anchor, values in data.items()}


def new_results(baseline: dict[str, list[str]], current: dict[str, list[str]]) -> dict[str, list[str]]:
    """Return result keys that are absent from the baseline."""

    changes: dict[str, list[str]] = {}
    for anchor, values in current.items():
        additions = sorted(set(values) - set(baseline.get(anchor, [])))
        if additions:
            changes[anchor] = additions
    return changes


def resolved_results(baseline: dict[str, list[str]], current: dict[str, list[str]]) -> dict[str, list[str]]:
    """Return baseline result keys that are absent from the current snapshot."""

    changes: dict[str, list[str]] = {}
    for anchor, values in baseline.items():
        resolved = sorted(set(values) - set(current.get(anchor, [])))
        if resolved:
            changes[anchor] = resolved
    return changes


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    record = subparsers.add_parser("record")
    record.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    record.add_argument("--out", type=Path, required=True)
    record.add_argument("--anchor", action="append", dest="anchors")
    compare = subparsers.add_parser("compare")
    compare.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--anchor", action="append", dest="anchors")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the baseline recording or comparison command."""

    options = _parser().parse_args(argv)
    if options.command == "record":
        save_baseline(snapshot(options.root, options.anchors), options.out)
        return 0

    baseline = load_baseline(options.baseline)
    current = snapshot(options.root, options.anchors)
    additions = new_results(baseline, current)
    resolutions = resolved_results(baseline, current)
    for anchor in sorted(additions):
        for result in additions[anchor]:
            print(f"NEW {anchor} {result}")
    for anchor in sorted(resolutions):
        for result in resolutions[anchor]:
            print(f"RESOLVED {anchor} {result}")
    return 1 if additions or current.get("__errors__") else 0


if __name__ == "__main__":
    raise SystemExit(main())
