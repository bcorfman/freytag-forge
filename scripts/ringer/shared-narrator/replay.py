# ruff: noqa: E501
"""Billed frozen-payload replay for the shared-narrator comparisons A, B, C (see .plans/shared-narrator-instruction-conflicts-prereg.md).

Usage (repo root, inside a Ringer probe task):
  .venv/bin/python scripts/ringer/shared-narrator/replay.py COMPARISON FROZEN.json OUT.json FIRST LAST [--confirm]
COMPARISON is A, B or C. Without --confirm nothing is sent: the script prints the request count and exits.
Interleaved sample-major, endpoint, arm (C0 then the candidate). One request per cell, no retries or replacements,
every error kept as a row. Only the model request is replayed: no matcher, judge or capture calls, and the
appended delivery and cues are composed later by the scorer, not here."""

import json
import sys
from pathlib import Path

ENDPOINTS = {"A": ("A1", "A2", "A3"), "B": ("H1", "H2"), "C": ("H1", "H2")}
REQUEST_CAP = {"A": 72, "B": 48, "C": 48}
args = [a for a in sys.argv[1:] if a != "--confirm"]
confirm = "--confirm" in sys.argv
comparison, frozen_path, out_path, first, last = args[0], Path(args[1]), Path(args[2]), int(args[3]), int(args[4])
assert comparison in ENDPOINTS and 1 <= first <= last <= 12
frozen = json.loads(frozen_path.read_text())
endpoints = ENDPOINTS[comparison]
planned = (last - first + 1) * len(endpoints) * 2
assert planned <= REQUEST_CAP[comparison], f"{planned} requests exceeds the {REQUEST_CAP[comparison]} cap"
print(f"comparison {comparison}: endpoints {endpoints}, samples {first}-{last}, requests {planned}")
if not confirm:
    print("dry run: no request sent (pass --confirm to bill)")
    raise SystemExit(0)

from bench.core import load_dotenv, load_variation, seeded_state_for_scene  # noqa: E402

load_dotenv()
from bench.frozen_prompts import _decode_replay_body, _offline_capture_provider  # noqa: E402

root = frozen_path.parent
eps = frozen["endpoints"]
send = {}
for eid in endpoints:
    variation = load_variation(root / f"variation-{eid}.json")
    _, state = seeded_state_for_scene(variation, eps[eid]["scene"])
    send[eid] = _offline_capture_provider(state)._send_http
rows = []
for sample in range(first, last + 1):
    for eid in endpoints:
        for arm in ("C0", comparison):
            row = {
                "arm": arm,
                "id": eid,
                "sample": sample,
                "command": eps[eid]["command"],
                "narration": None,
                "error": None,
                "raw": None,
            }
            try:
                body = send[eid](frozen["arms"][arm][eid]["payload"])
                row["raw"] = body.decode("utf-8", errors="replace")
                row["narration"] = _decode_replay_body(body)
                print(arm, eid, sample, "ok", flush=True)
            except Exception as error:
                row["error"] = str(error)
                print(arm, eid, sample, "error", flush=True)
            rows.append(row)
            out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
