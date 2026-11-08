# ruff: noqa: E501
"""Payload match: the real engine, run on the 3A script prefix, must produce the same system and user text as the frozen GU arm
(bench/results/shared-narrator/g/frozen-GU.json) at c4, c5, c9. Zero model calls (network stubbed by bench.frozen_prompts).
Run: TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/gu_match.py"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
from bench.core import load_variation  # noqa: E402

frozen = json.loads(
    (ROOT / "bench/results/shared-narrator/g" / (sys.argv[1] if len(sys.argv) > 1 else "frozen-GU.json")).read_text()
)
fp.SCENE = "3A"
variation = load_variation(ROOT / "bench/variations/richer-3a-loc-P.json")
fp._script_inputs(variation)
states, inputs = fp._prefix_states(variation, [4, 5, 9])
bad = 0
for ep in frozen["endpoints"]:
    n = ep["n"]
    payload, _ = fp._capture_wire_payload(copy.deepcopy(states[n - 1]), inputs[n - 1])
    for part in ("system", "user"):
        same = payload[part] == ep["wire_payload"][part]
        print(f"c{n} {part}: {'MATCH' if same else 'DIFFERS'}")
        if not same:
            bad += 1
            a, b = payload[part].split("\n"), ep["wire_payload"][part].split("\n")
            for line in [x for x in a if x not in b][:6]:
                print("   engine only:", line[:200])
            for line in [x for x in b if x not in a][:6]:
                print("   frozen only:", line[:200])
sys.exit(1 if bad else 0)
