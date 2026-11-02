"""Offline checker for Act 3A probe artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .act3a_probe import CAPS, MAX_COMMANDS, ROW_FIELDS
except ImportError:
    from act3a_probe import CAPS, MAX_COMMANDS, ROW_FIELDS


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
    for row in rows:
        row_id = row.get("row_id", "<row>")
        missing = [field for field in ROW_FIELDS if field not in row]
        if missing:
            errors.append(f"WHY {row_id} is missing fields: {', '.join(missing)}")
        if row.get("scene") != "3A":
            errors.append(f"WHY {row_id}: scene must be '3A'")
        if row.get("ledger") not in {"transmit", "rescue"}:
            errors.append(f"WHY {row_id}: ledger must be transmit or rescue")
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
        if mode == "dry":
            if row.get("ended_by") != "scene_3b":
                errors.append(f"WHY {row_id}: dry run must end in scene_3b")
            if row.get("exit_cause") != "earned_transition":
                errors.append(f"WHY {row_id}: dry run must have an earned transition")
            if row.get("reunion_text_unhurried") is not True:
                errors.append(f"WHY {row_id}: reunion must contain unhurried")
            if row.get("signal_text_gives_signal") is not True:
                errors.append(f"WHY {row_id}: signal must contain gives/give the signal")
            required = {"michelle_reached", "uprising_prepared", "detention_uprising_started"}
            missing_facts = required - set(row.get("final_true_facts", []))
            if missing_facts:
                errors.append(f"WHY {row_id}: missing final facts: {', '.join(sorted(missing_facts))}")
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
    print("act3a probe artifacts pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
