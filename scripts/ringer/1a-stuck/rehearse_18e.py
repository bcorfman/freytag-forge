"""Round 18e: the first story-data ticket the planner fixes end to end (1A stuck turns).

Stations 4 (Sonnet planner picks the fix, real Ringer wiring), 5, 6 and 9 (real gh, real merge) on one
`merge_to_main` ticket built from the packets of a saved smoke report.
Stops after station 9 hands the ticket to station 7; the billed smoke is a separate go.
Usage: rehearse_18e.py WORKSPACE PACKETS [--resume]  (resume skips stations 4 to 6 and reruns station 9
on the existing ticket tree)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from factory.guard import LimitSleep
from factory.stations.deliver import deliver_handler
from factory.stations.free_gates import free_gates_handler
from factory.stations.fun_review import fun_review_handler
from factory.stations.planner import default_planner
from factory.stations.prompt_snapshot import prompt_snapshot_handler
from factory.stations.wiring import wiring_handler
from factory.tickets import Station, Ticket, TicketClass

ROOT = Path(os.environ.get("FACTORY_ROOT") or Path(__file__).resolve().parents[3])
TICKET_ID = "factory-18e-1A-story_data"


def _env() -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": f"{ROOT}:{ROOT}/packages/worldkeeper/src"}


def _record_baselines(workspace: Path) -> None:
    python = str(ROOT / ".venv/bin/python")
    gap = workspace / "gap_baseline.json"
    prompts = workspace / "prompts"
    if not gap.exists():
        subprocess.run(
            [python, "-m", "factory.checks.gap_delta", "record", "--out", str(gap)], cwd=ROOT, env=_env(), check=True
        )
    if not prompts.exists():
        subprocess.run(
            [python, "-m", "factory.stations.prompt_snapshot", "record", "--scene", "1A", "--out", str(prompts)],
            cwd=ROOT,
            env=_env(),
            check=True,
        )


def main(workspace: Path, packets_path: Path) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    _record_baselines(workspace)
    packets = [p for p in json.loads(packets_path.read_text(encoding="utf-8")) if p["scene"] == "1A"]
    now = datetime.now(UTC)
    iso = now.isoformat()
    ticket = Ticket(
        id=TICKET_ID,
        scene="1A",
        station=Station.WIRING,
        ticket_class=TicketClass.STORY_DATA,
        token_budget=400_000,
        created_at=iso,
        updated_at=iso,
        payload={
            "scene": "1A",
            "failing_turns": packets,
            "merge_to_main": True,
            "review_criteria_path": str(ROOT / ".plans/game-reimagination/whole-story-pacing.md"),
            "workspace": str(workspace / "work"),
            "gap_baseline": str(workspace / "gap_baseline.json"),
            "baseline_dir": str(workspace / "prompts"),
            "source_root": "data/stories/continuity-initiative/source",
            "tests": ["tests/test_game_path_completion.py"],
            "carry_matrix": True,
            "carry_scenes": ["1A"],
        },
    )
    saved_plan = workspace / "work" / TICKET_ID / "plan.json"
    if "--reuse-plan" in sys.argv and saved_plan.is_file():
        ticket.payload["plan"] = json.loads(saved_plan.read_text(encoding="utf-8"))
        print("reusing the saved planner plan", flush=True)
    print(f"packets: {len(packets)}", flush=True)
    resume = "--resume" in sys.argv
    for name, handler in (
        ()
        if resume
        else (
            ("4 wiring", wiring_handler(ROOT, planner=default_planner(ROOT))),
            ("5 free gates", free_gates_handler(ROOT)),
            ("6 prompt snapshot", prompt_snapshot_handler(ROOT)),
            ("10 fun review", fun_review_handler(ROOT)),
        )
    ):
        outcome = handler(ticket, datetime.now(UTC))
        print(f"station {name}:", outcome.passed, outcome.check, "\n", outcome.output[-1500:], flush=True)
        if not outcome.passed:
            return 1
    if "--deliver" not in sys.argv:
        print("held: station 9 not run (pass --deliver to merge)", flush=True)
        return 0
    deliver = deliver_handler(ROOT)
    deadline = time.time() + 3 * 3600
    while time.time() < deadline:
        now = datetime.now(UTC)
        try:
            outcome = deliver(ticket, now)
        except LimitSleep as sleep:
            wait = max(30.0, (sleep.resume_at - now).total_seconds()) if sleep.resume_at else 120.0
            print(f"{now:%H:%M:%S} station 9 waits on {sleep.provider} for {wait:.0f}s", flush=True)
            time.sleep(wait)
            continue
        print("station 9:", outcome.passed, outcome.check, outcome.output, outcome.payload_updates, flush=True)
        return 0 if outcome.passed else 1
    print("station 9: gave up after 3 hours", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
