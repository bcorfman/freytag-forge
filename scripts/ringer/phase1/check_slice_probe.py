"""Offline checker for phase-1 slice probe artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from .slice_probe import CAPS, ROW_FIELDS
except ImportError:
    from slice_probe import CAPS, ROW_FIELDS


def check(out: Path, n: int, mode: str) -> list[str]:
    errors: list[str] = []
    path = out / "results.json"
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return [f"WHY results.json cannot be read: {error}"]
    if artifact.get("mode") != mode:
        errors.append(f"WHY results.json mode is {artifact.get('mode')!r}, expected {mode!r}")
    rows = artifact.get("rows")
    if not isinstance(rows, list) or len(rows) != n:
        errors.append(f"WHY results.json must contain exactly {n} row(s)")
        rows = rows if isinstance(rows, list) else []
    if artifact.get("caps") != CAPS:
        errors.append("WHY cap fields must be exactly Cloudflare 80 and player 40")
    for row in rows:
        missing = [field for field in ROW_FIELDS if field not in row]
        if missing:
            errors.append(f"WHY {row.get('row_id', '<row>')} is missing fields: {', '.join(missing)}")
        if row.get("arm") != "current":
            errors.append(f"WHY {row.get('row_id')}: arm must be current")
        if len(row.get("commands", [])) != len(row.get("responses", [])):
            errors.append(f"WHY {row.get('row_id')}: commands and responses must have equal length")
        if len(row.get("commands", [])) > 30:
            errors.append(f"WHY {row.get('row_id')}: command cap is 30")
        if any(item.get("stale") for item in row.get("stale_cues", [])):
            errors.append(f"WHY {row.get('row_id')}: stale cue detected")
        for field in ("clarification_count", "rejection_count", "segments_dropped", "request_count", "recovery_count"):
            if type(row.get(field)) is not int or row[field] < 0:
                errors.append(f"WHY {row.get('row_id')}: {field} must be a non-negative integer")
    raw = "".join(path.read_text(encoding="utf-8") for path in out.glob("**/*") if path.is_file())
    if re.search(r"(?:token|secret|authorization|api[_-]?key)\s*[:=]\s*[^\s}\"]+", raw, re.I):
        errors.append("WHY an artifact appears to contain a secret or token")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", type=Path)
    parser.add_argument("n", type=int)
    parser.add_argument("--mode", choices=("dry", "artifacts"), required=True)
    args = parser.parse_args()
    errors = check(args.dir, args.n, "live" if args.mode == "artifacts" else "dry")
    if errors:
        print("\n".join(errors))
        return 1
    print("slice probe artifacts pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
