# ruff: noqa: E501
"""Amendment 20 billed replay: C/S x (c4, c5, c9) x samples FIRST..LAST, interleaved (sample-major, endpoint, arm).
Usage (repo root, inside a Ringer probe task): .venv/bin/python scripts/ringer/3a-open-issues/speech_replay.py OUT.json FIRST LAST
One request per cell, no retries or replacements, every error kept as a row. 12 samples = 72 requests."""

import json
import sys
from pathlib import Path

from bench.core import load_dotenv

load_dotenv()
from bench.frozen_prompts import _decode_replay_body, _default_transport  # noqa: E402

root = Path("bench/results/richer-3a-probe/speech")
out = Path(sys.argv[1])
first, last = int(sys.argv[2]), int(sys.argv[3])
frozen = {arm: json.loads((root / f"frozen-{arm}.json").read_text()) for arm in "CS"}
transport = _default_transport(frozen["S"])
rows = []
for sample in range(first, last + 1):
    for n in (4, 5, 9):
        for arm in "CS":
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
