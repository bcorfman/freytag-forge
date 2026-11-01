"""Offline checker for Act 2 probe artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from .act2_probe import CAPS, PREFIXES, ROW_FIELDS, SCENES, SCRIPTED_PREFIXES
except ImportError:
    from act2_probe import CAPS, PREFIXES, ROW_FIELDS, SCENES, SCRIPTED_PREFIXES

OUTCOME_FACTS_2C = {
    "committed_to_transmit",
    "committed_to_rescue",
    "detention_sectors_sealed",
    "evidence_not_transmitted",
}
ALLOWED_EXIT_CAUSES = {
    "inspection_convincing",
    "inspection_doubted",
    "brandon_name_kept",
    "brandon_name_erased",
    "committed_to_transmit",
    "committed_to_rescue",
    "missed_window_plus_recovery",
    "neutral_recovery",
    "other",
}


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
        row_id = row.get("row_id", "<row>")
        missing = [field for field in ROW_FIELDS if field not in row]
        if missing:
            errors.append(f"WHY {row_id} is missing fields: {', '.join(missing)}")
        scene = row.get("scene")
        if scene not in SCENES:
            errors.append(f"WHY {row_id}: scene must be one of {SCENES}")
        if row.get("arm") != "current":
            errors.append(f"WHY {row_id}: arm must be current")
        if row.get("prefix") not in PREFIXES:
            errors.append(f"WHY {row_id}: prefix must be one of {tuple(PREFIXES)}")
        if row.get("exit_cause") not in ALLOWED_EXIT_CAUSES:
            errors.append(f"WHY {row_id}: exit_cause is not a declared Act 2 classification")
        if type(row.get("scripted_turns")) is not int or row["scripted_turns"] < 0:
            errors.append(f"WHY {row_id}: scripted_turns must be a non-negative integer")
        for field in ("nudge_seen_turn", "withdrawal_seen_turn", "exit_seen_turn"):
            if row.get(field) is not None and (type(row[field]) is not int or row[field] < 1):
                errors.append(f"WHY {row_id}: {field} must be a positive integer or null")
        for field in ("turns_in_scene", "turns_in_1c"):
            if type(row.get(field)) is not int or row[field] < 0:
                errors.append(f"WHY {row_id}: {field} must be a non-negative integer")
        commands = row.get("commands", [])
        responses = row.get("responses", [])
        if not isinstance(commands, list) or not isinstance(responses, list) or len(commands) != len(responses):
            errors.append(f"WHY {row_id}: commands and responses must have equal length")
        if len(commands) > 30:
            errors.append(f"WHY {row_id}: command cap is 30")
        if type(row.get("request_count")) is int and row["request_count"] > CAPS["cloudflare"]:
            errors.append(f"WHY {row_id}: Cloudflare request cap is 80")
        if any(item.get("stale") for item in row.get("stale_cues", [])):
            errors.append(f"WHY {row_id}: stale cue detected")
        for field in ("clarification_count", "rejection_count", "segments_dropped", "request_count", "recovery_count"):
            if type(row.get(field)) is not int or row[field] < 0:
                errors.append(f"WHY {row_id}: {field} must be a non-negative integer")
        turns = row.get("turns")
        if not isinstance(turns, list) or len(turns) != len(commands):
            errors.append(f"WHY {row_id}: turns must have one record per command")
            turns = turns if isinstance(turns, list) else []
        required_turn_fields = (
            "turn",
            "scene_before",
            "scene_after",
            "facts_newly_asserted",
            "facts_retracted",
            "committed_reveals",
            "reveal_selection",
            "last_attempt_rejection",
            "transition_cause",
            "request_count_delta",
            "recovery_count_delta",
            "staged_cue_fact_id",
            "staged_handoff_fact_ids",
            "delivered_cue_ids",
            "segments_dropped",
            "repeated_response",
            "scripted",
        )
        for turn in turns:
            missing_turn = [field for field in required_turn_fields if field not in turn]
            if missing_turn:
                errors.append(f"WHY {row_id}: turn record missing fields: {', '.join(missing_turn)}")
                continue
            for field in (
                "facts_newly_asserted",
                "facts_retracted",
                "committed_reveals",
                "staged_handoff_fact_ids",
                "delivered_cue_ids",
            ):
                if not isinstance(turn[field], list) or turn[field] != sorted(turn[field]):
                    errors.append(f"WHY {row_id}: turn {turn.get('turn')} {field} must be sorted list")
            for field in ("request_count_delta", "recovery_count_delta", "segments_dropped"):
                if type(turn[field]) is not int or turn[field] < 0:
                    errors.append(f"WHY {row_id}: turn {turn.get('turn')} {field} must be non-negative integer")
            for field in ("repeated_response", "scripted"):
                if type(turn[field]) is not bool:
                    errors.append(f"WHY {row_id}: turn {turn.get('turn')} {field} must be boolean")
            if not isinstance(turn["reveal_selection"], dict):
                errors.append(f"WHY {row_id}: turn {turn.get('turn')} reveal_selection must be an object")
        if type(row.get("repeated_response_streak_max")) is not int or row["repeated_response_streak_max"] < 1:
            errors.append(f"WHY {row_id}: repeated_response_streak_max must be a positive integer")
        if not isinstance(row.get("final_true_facts"), list) or row["final_true_facts"] != sorted(
            row["final_true_facts"]
        ):
            errors.append(f"WHY {row_id}: final_true_facts must be a sorted list")
        if not isinstance(row.get("unearned_facts"), list) or row["unearned_facts"] != sorted(row["unearned_facts"]):
            errors.append(f"WHY {row_id}: unearned_facts must be a sorted list")
        if type(row.get("stuck_loop")) is not bool:
            errors.append(f"WHY {row_id}: stuck_loop must be boolean")
        scripted_turns = sum(bool(turn.get("scripted")) for turn in turns)
        if row.get("scripted_turns") != scripted_turns:
            errors.append(f"WHY {row_id}: scripted_turns does not match turn records")
        if row.get("prefix") == "none" and scripted_turns:
            errors.append(f"WHY {row_id}: prefix none cannot have scripted turns")
        if row.get("prefix") in PREFIXES and row.get("prefix") != "none" and scene in SCENES:
            expected = min(len(SCRIPTED_PREFIXES[row["prefix"]][scene]), row["turns_in_scene"])
            if scripted_turns != expected:
                errors.append(f"WHY {row_id}: prefix {row['prefix']} must have {expected} scripted turns")
        if scene == "2C" and row.get("prefix") in {"missed_window", "stall"}:
            forbidden = OUTCOME_FACTS_2C & set(row.get("final_true_facts", []))
            if forbidden:
                errors.append(f"WHY {row_id}: 2C recovery cannot assert outcome facts: {', '.join(sorted(forbidden))}")
            if row.get("unearned_facts"):
                errors.append(f"WHY {row_id}: 2C missed-window/stall unearned_facts must be empty")
    raw = "".join(file.read_text(encoding="utf-8") for file in out.glob("**/*") if file.is_file())
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
    print("act2 probe artifacts pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
