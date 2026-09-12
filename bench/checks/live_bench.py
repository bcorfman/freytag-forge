"""Acceptance check for the Phase 6 live benchmark run.

Reads the artifacts a `bench run` produced and decides whether the Phase 6 exit
gate is met. It never calls a model itself - it only judges what the run left
behind - so it is safe to re-run while reviewing.

Usage: check_live_bench.py <run-dir> [<run-dir> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FAILURES: list[str] = []
NOTES: list[str] = []

HANDOFF_ID = "k_sl_1a_b_r2"
# The failure codes that stopped every previous attempt before the recording turn.
BLOCKER_CODES = ("uncited_knowledge", "narration_known_term_leak")


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        FAILURES.append(f"{path} is missing; the bench run did not produce its artifacts")
    except json.JSONDecodeError as exc:
        FAILURES.append(f"{path} is not valid JSON: {exc}")
    return None


def check_run(run_dir: Path) -> None:
    summary = load(run_dir / "summary.json")
    records = load(run_dir / "all-turn-records.json")
    if summary is None or records is None:
        return

    label = run_dir.name
    budget = summary.get("budget") or {}
    turns = budget.get("actual_narration_turns")
    if not turns:
        FAILURES.append(
            f"[{label}] actual_narration_turns is {turns!r}; the run narrated nothing, so it proves nothing about "
            "the authored handoff"
        )
    else:
        NOTES.append(f"[{label}] narrated {turns} turns")

    # The summary must now be able to speak about failure at all (round-1 bench fix).
    if "failed_replicates" not in summary:
        FAILURES.append(
            f"[{label}] summary.json has no failed_replicates field, so a failed run is still indistinguishable "
            "from one that never executed"
        )
    failed = summary.get("failed_replicates", 0)
    blob = json.dumps(summary)
    hit = [code for code in BLOCKER_CODES if code in blob]
    if hit:
        FAILURES.append(
            f"[{label}] the run still failed with {', '.join(hit)} - the pre-recording narration-safety blockers "
            f"Phase 6 was waiting on are not cleared ({failed} failed replicate(s)). Read summary.json for the "
            "exact failure_reason."
        )
    elif failed:
        NOTES.append(f"[{label}] {failed} replicate(s) failed, but not on the Phase 6 blocker codes")

    runs = records.get("runs", []) if isinstance(records, dict) else records
    entries = [turn for run in runs if isinstance(run, dict) for turn in (run.get("turns") or [])]
    for run in runs:
        reason = isinstance(run, dict) and run.get("failure_reason")
        if reason:
            NOTES.append(f"[{label}] replicate {run.get('replicate')} ({run.get('script')}) failed: {reason}")
            if any(code in str(reason) for code in BLOCKER_CODES):
                FAILURES.append(
                    f"[{label}] replicate {run.get('replicate')} still hit a pre-recording narration-safety "
                    f"blocker: {reason}"
                )
    handoffs = [
        entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("authored_handoff_candidate_id") == HANDOFF_ID
    ]
    offered = [entry for entry in entries if isinstance(entry, dict) and entry.get("authored_handoff_candidate_id")]
    NOTES.append(f"[{label}] {len(entries)} turn record(s), {len(offered)} with an authored handoff attributed")
    if handoffs:
        NOTES.append(f"[{label}] authored handoff {HANDOFF_ID} composed on {len(handoffs)} turn(s)")
    return


def main(argv: list[str]) -> int:
    dirs = [Path(value) for value in argv[1:]]
    if not dirs:
        print("usage: check_live_bench.py <run-dir> [<run-dir> ...]", file=sys.stderr)
        return 2
    for run_dir in dirs:
        check_run(run_dir)

    # The exit gate wants the authored delivery actually reached, in at least one run.
    reached = any("authored handoff k_sl_1a_b_r2 composed" in note for note in NOTES)
    if not reached and not FAILURES:
        FAILURES.append(
            f"no run composed the authored handoff {HANDOFF_ID}. The blocker codes are cleared, but the scripts "
            "still did not reach the recording action, so the exit gate's 'accepted delivery' evidence is missing. "
            "Report how far each script got rather than treating this as a pass."
        )

    for note in NOTES:
        print(f"  . {note}")
    if FAILURES:
        print("FAIL: Phase 6 live benchmark exit gate", file=sys.stderr)
        for line in FAILURES:
            print(f"  - {line}", file=sys.stderr)
        return 1
    print("PASS: the pre-recording blockers are cleared and the authored handoff delivered live.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
