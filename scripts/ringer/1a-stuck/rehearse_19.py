"""Round 19 rerun: ticket 1A end to end through the real FactoryLine, starting at station 11.

Stations 11 (diagnose), 4 (plan + Ringer wiring), 5, 6, 12 (probe, billed), 10 (fun review), then 9 and the
live playtest. The line does the routing (probe reject -> replan, fun block -> replan, owner escalation).
Stops before station 9 (the merge) unless --deliver is passed; re-run with --resume --deliver to continue the
same ticket from the queue in WORKSPACE.
Usage: rehearse_19.py WORKSPACE REPORT [--deliver] [--resume]
  REPORT is the saved smoke report whose typed commands the probe replays (e2e-blind-player-17c.json);
  packets come from the same report through report_to_packets.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from factory.breakers import FileNotifier
from factory.line import FactoryLine
from factory.state import FactoryState
from factory.stations import build_handlers
from factory.tickets import Station, Status, Ticket, TicketClass, TicketQueue

ROOT = Path(os.environ.get("FACTORY_ROOT") or Path(__file__).resolve().parents[3])
TICKET_ID = "factory-19-1A-story_data"


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


def _packets(report_path: Path) -> list[dict]:
    from factory.stations.live_playtest import report_to_packets  # noqa: PLC0415

    report = json.loads(report_path.read_text(encoding="utf-8"))
    return [p for p in report_to_packets(report, key_prefix="smoke17c-") if p["scene"] == "1A"]


def main(workspace: Path, report_path: Path) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    queue = TicketQueue(workspace / "tickets")
    now = datetime.now(UTC)
    if "--resume" not in sys.argv:
        _record_baselines(workspace)
        packets = _packets(report_path)
        iso = now.isoformat()
        queue.save(
            Ticket(
                id=TICKET_ID,
                scene="1A",
                station=Station.DIAGNOSE,
                ticket_class=TicketClass.STORY_DATA,
                token_budget=600_000,
                created_at=iso,
                updated_at=iso,
                payload={
                    "scene": "1A",
                    "failing_turns": packets,
                    "report_path": str(report_path),
                    "billed_run_approved": True,
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
        )
        print(f"packets: {len(packets)}", flush=True)
    state = FactoryState.load(workspace / "state.json")
    line = FactoryLine(
        queue=queue,
        state=state,
        handlers=build_handlers(ROOT),
        provider_for=lambda ticket: ticket.provider or ticket.payload.get("provider"),
        check_breakers=lambda when: [],
        notifier=FileNotifier(workspace / "notices.txt"),
    )
    deliver = "--deliver" in sys.argv
    while True:
        ticket = queue.get(TICKET_ID)
        if ticket.status is Status.PASSED:
            print("ticket passed", flush=True)
            return 0
        if not deliver and ticket.station is Station.DELIVER and ticket.status is Status.QUEUED:
            print("held before station 9 (merge); re-run with --resume --deliver", flush=True)
            return 0
        outcome = line.step(datetime.now(UTC))
        after = queue.get(TICKET_ID)
        print(
            f"{datetime.now(UTC):%H:%M:%S} {ticket.station.name} -> {outcome.kind} "
            f"(now {after.station.name} {after.status.value}, tokens {after.tokens_used})",
            flush=True,
        )
        if outcome.kind in {"halted", "idle"}:
            print(
                f"stopped: {outcome.kind}; status {after.status.value}; payload owner_wait: "
                f"{after.payload.get('owner_wait')}",
                flush=True,
            )
            return 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
