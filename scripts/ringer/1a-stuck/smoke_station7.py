"""Station 7 billed smoke on one scene: waits for staging to report SHA, then runs the live playtest.

Usage (with .env sourced): smoke_station7.py TICKET_ID SCENE REPLICATES SHA MAX_USD [TURN_CAP]
Needs the owner's go for each billed run; sets billed_run_approved itself.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from factory.stations.live_playtest import live_playtest_handler
from factory.tickets import Station, Ticket

ROOT = Path(__file__).resolve().parents[3]


def _staging_sha() -> str | None:
    url = os.environ.get("E2E_API_BASE_URL", "").rstrip("/") + "/api/v1/version"
    request = urllib.request.Request(url, headers={"User-Agent": "freytag-factory/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response).get("sha")
    except Exception:
        return None


def main(ticket_id: str, scene: str, replicates: int, sha: str, max_usd: float, turn_cap: int | None) -> int:
    deadline = time.time() + 45 * 60
    while _staging_sha() != sha:
        if time.time() > deadline:
            print(f"staging never reached {sha}", flush=True)
            return 2
        print(f"{datetime.now(UTC):%H:%M:%S} waiting for staging {sha[:8]}", flush=True)
        time.sleep(60)
    now = datetime.now(UTC)
    ticket = Ticket(
        id=ticket_id,
        scene=scene,
        station=Station.LIVE_PLAYTEST,
        token_budget=400_000,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        payload={
            "scene": scene,
            "profile": "canonical",
            "replicates": replicates,
            "expected_sha": sha,
            "billed_run_approved": True,
            "max_usd": max_usd,
            **({"turn_cap": turn_cap} if turn_cap else {}),
        },
    )
    result = live_playtest_handler(ROOT)(ticket, now)
    print("station 7:", result.passed, result.check, "\n", result.output, flush=True)
    print("failing turn packets:", len(result.turns or []), flush=True)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(
        main(
            sys.argv[1],
            sys.argv[2],
            int(sys.argv[3]),
            sys.argv[4],
            float(sys.argv[5]),
            int(sys.argv[6]) if len(sys.argv) > 6 else None,
        )
    )
