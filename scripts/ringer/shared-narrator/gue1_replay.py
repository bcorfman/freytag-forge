# ruff: noqa: E501
"""Billed replay for experiment GUE1: OLD/EMB x (R1, R2) x samples FIRST..LAST, interleaved (sample-major, endpoint, arm).
Usage (repo root, inside a Ringer probe task): .venv/bin/python scripts/ringer/shared-narrator/gue1_replay.py OUT.json FIRST LAST --confirm
One request per cell, no retries or replacements, every error kept as a row. 12 samples = 48 requests. Refuses without --confirm."""

import json
import sys
from pathlib import Path

ARMS = ("OLD", "EMB")
ENDPOINTS = ("R1", "R2")
args = [a for a in sys.argv[1:] if a != "--confirm"]
out, first, last = Path(args[0]), int(args[1]), int(args[2])
assert 1 <= first <= last <= 12 and (last - first + 1) * 4 <= 48
print(f"requests {(last - first + 1) * 4}")
if "--confirm" not in sys.argv:
    print("dry run: nothing sent")
    raise SystemExit(0)

from bench.core import load_dotenv  # noqa: E402

load_dotenv()
from bench.frozen_prompts import _decode_replay_body, _default_transport  # noqa: E402

root = Path("bench/results/shared-narrator/g")
frozen = {arm: json.loads((root / f"frozen-GUE1-{arm}.json").read_text()) for arm in ARMS}
transport = _default_transport(frozen["EMB"])
rows = []
for sample in range(first, last + 1):
    for n in ENDPOINTS:
        for arm in ARMS:
            endpoint = next(e for e in frozen[arm]["endpoints"] if e["n"] == n)
            row = {
                "arm": arm,
                "n": n,
                "sample": sample,
                "command": endpoint["command"],
                "narration": None,
                "error": None,
                "raw": None,
            }
            try:
                body = transport(endpoint["wire_payload"])
                row["raw"] = body.decode("utf-8", errors="replace")
                row["narration"] = _decode_replay_body(body)
                print(arm, n, sample, "ok", flush=True)
            except Exception as error:
                row["error"] = str(error)
                print(arm, n, sample, "error", flush=True)
            rows.append(row)
            out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
