"""Round 18b-4: rehearse stations 4, 5 and 6 on the saved 1A stuck turns.

Real Sonnet plan, real Ringer wiring, free gates and prompt snapshot on the ticket tree.
Stops before any merge. Usage: rehearse_18b4.py WORKSPACE REPORT
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from factory.line import StationResult
from factory.stations.free_gates import free_gates_handler
from factory.stations.live_playtest import report_to_packets
from factory.stations.planner import default_planner
from factory.stations.prompt_snapshot import prompt_snapshot_handler
from factory.stations.wiring import wiring_handler
from factory.tickets import Station, Ticket

ROOT = Path(__file__).resolve().parents[3]


def main(workspace: Path, report_path: Path) -> int:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    packets = [p for p in report_to_packets(report, key_prefix="smoke17c-") if p["scene"] == "1A"]
    now = datetime.now(UTC)
    iso = now.isoformat()
    ticket = Ticket(
        id="rehearse-18b4-1A-story_data",
        scene="1A",
        station=Station.WIRING,
        token_budget=400_000,
        created_at=iso,
        updated_at=iso,
        payload={
            "scene": "1A",
            "failing_turns": packets,
            "workspace": str(workspace / "work"),
            "gap_baseline": str(workspace / "gap_baseline.json"),
            "baseline_dir": str(workspace / "prompts"),
            "source_root": "data/stories/continuity-initiative/source",
            "tests": ["tests/test_game_path_completion.py"],
            "carry_matrix": True,
            "carry_scenes": ["1A"],
        },
    )
    print(f"packets: {len(packets)}", flush=True)
    results: list[tuple[str, StationResult]] = []
    wired = wiring_handler(ROOT, planner=default_planner(ROOT))(ticket, now)
    results.append(("4 wiring", wired))
    print("station 4:", wired.passed, wired.check, "\n", wired.output[-3000:], flush=True)
    if wired.passed:
        for name, handler in (
            ("5 free gates", free_gates_handler(ROOT)),
            ("6 prompt snapshot", prompt_snapshot_handler(ROOT)),
        ):
            outcome = handler(ticket, now)
            results.append((name, outcome))
            print(f"station {name}:", outcome.passed, outcome.check, "\n", outcome.output[-3000:], flush=True)
            if not outcome.passed:
                break
    return 0 if all(r.passed for _, r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
