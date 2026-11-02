"""Offline checker for Act 3C probe artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .act3c_probe import CAPS, MAX_COMMANDS, NEUTRAL_COMMANDS, PREFIXES, ROW_FIELDS
except ImportError:
    from act3c_probe import CAPS, MAX_COMMANDS, NEUTRAL_COMMANDS, PREFIXES, ROW_FIELDS


EXPECTED = {
    "none": ("evacuation_clean", "barrier_held"),
    "clean": ("evacuation_clean", "barrier_held"),
    "costly": ("evacuation_costly", "lower_levels_lost"),
    "stall": ("neutral_recovery", "surge_forced_evacuation"),
}


def check(out: Path, n: int, mode: str) -> list[str]:
    try:
        artifact = json.loads((out / "results.json").read_text(encoding="utf-8"))
    except Exception as error:
        return [f"WHY results.json cannot be read: {error}"]
    errors: list[str] = []
    expected_mode = "dry" if mode == "dry" else "live"
    if artifact.get("mode") != expected_mode:
        errors.append(f"WHY results.json mode is {artifact.get('mode')!r}, expected {expected_mode!r}")
    rows = artifact.get("rows")
    if not isinstance(rows, list) or len(rows) != n:
        errors.append(f"WHY results.json must contain exactly {n} row(s)")
        rows = rows if isinstance(rows, list) else []
    if artifact.get("caps") != CAPS:
        errors.append("WHY cap fields must be exactly Cloudflare 80 and player 40")
    failure_exists = (out / "run-failure.txt").exists()
    for row in rows:
        row_id = row.get("row_id", "<row>")
        missing = [field for field in ROW_FIELDS if field not in row]
        if missing:
            errors.append(f"WHY {row_id} is missing fields: {', '.join(missing)}")
        if row.get("scene") != "3C":
            errors.append(f"WHY {row_id}: scene must be '3C'")
        prefix = row.get("prefix")
        if prefix not in PREFIXES:
            errors.append(f"WHY {row_id}: unknown prefix {prefix!r}")
        commands = row.get("commands", [])
        responses = row.get("responses", [])
        if not isinstance(commands, list) or not isinstance(responses, list) or len(commands) != len(responses):
            errors.append(f"WHY {row_id}: commands and responses must have equal length")
        if isinstance(commands, list) and len(commands) > MAX_COMMANDS:
            errors.append(f"WHY {row_id}: command cap is {MAX_COMMANDS}")
        if any(item.get("stale") for item in row.get("stale_cues", [])):
            errors.append(f"WHY {row_id}: stale cue detected")
        if type(row.get("request_count")) is not int or row.get("request_count", 0) > CAPS["cloudflare"]:
            errors.append(f"WHY {row_id}: Cloudflare request cap is 80")
        if type(row.get("player_request_count")) is not int or row.get("player_request_count", 0) > CAPS["player"]:
            errors.append(f"WHY {row_id}: player request cap is 40")
        if not row.get("story_complete") and not failure_exists:
            errors.append(f"WHY {row_id}: story_complete is false without run-failure.txt")
        if mode == "dry" and prefix in EXPECTED:
            expected_exit, expected_variant = EXPECTED[prefix]
            if row.get("story_complete") is not True:
                errors.append(f"WHY {row_id}: dry run must complete the story")
            if row.get("exit_cause") != expected_exit:
                errors.append(f"WHY {row_id}: expected exit cause {expected_exit!r}")
            if expected_variant not in row.get("ending_variants_seen", []):
                errors.append(f"WHY {row_id}: expected ending variant {expected_variant!r}")
            if prefix == "stall" and commands != list(NEUTRAL_COMMANDS):
                errors.append("WHY stall dry run must contain exactly the eight neutral commands")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", type=Path)
    parser.add_argument("n", type=int)
    parser.add_argument("--mode", choices=("dry", "artifacts"), required=True)
    args = parser.parse_args()
    errors = check(args.dir, args.n, args.mode)
    if errors:
        print("\n".join(errors))
        return 1
    print("act3c probe artifacts pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
