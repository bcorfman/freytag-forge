# ruff: noqa: E501
"""Amendment 19 billed replay: C/P/L x (opening, c4, c5) x 12 samples, interleaved (sample-major, then endpoint, then arm).

Usage (inside a Ringer probe task, repo root): TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/3a-open-issues/location_replay.py OUT.json FIRST LAST
Samples FIRST..LAST inclusive (12 samples = 108 requests); three tasks of four samples each run side by side.
One request per cell, no retries, no replacements; every error is kept as a row. 108 requests at 12 samples.
"""

import json
import sys
from pathlib import Path

from bench.core import load_dotenv

load_dotenv()
from bench.frozen_prompts import _decode_replay_body, _default_transport  # noqa: E402

root = Path("bench/results/richer-3a-probe/loc")
out = Path(sys.argv[1])
first, last = int(sys.argv[2]), int(sys.argv[3])
frozen = {arm: json.loads((root / f"frozen-{arm}.json").read_text()) for arm in "CPL"}
transport = _default_transport(frozen["P"])
rows = []
for sample in range(first, last + 1):
    for n in (0, 4, 5):
        for arm in "CPL":
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
