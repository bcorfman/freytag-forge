# ruff: noqa: E501
"""Gate step 2: free count of speaker lines offered at 3A c4, c5, c9 with and without the narrated gate. Zero model calls.

TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/gate_lines.py OUT.json
"""

import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
import storygame.runtime.knowledge as kn  # noqa: E402
from bench.core import load_variation  # noqa: E402

OUT = Path(sys.argv[1])
fp.SCENE = "3A"
variation = load_variation(ROOT / "bench/variations/richer-3a-loc-P.json")
inputs = fp._script_inputs(variation)
states, inputs = fp._prefix_states(variation, [4, 5, 9])
real = kn.is_narrated
LINE = re.compile(r"^(.*?) may say this aloud: (.*)$", re.M)
result = {}
for label in (4, 5, 9):
    command = inputs[label - 1]
    row = {"command": command}
    for mode in ("gate_on", "gate_off"):
        kn.is_narrated = real if mode == "gate_on" else (lambda item, facts: True)
        payload, _ = fp._capture_wire_payload(copy.deepcopy(states[label - 1]), command)
        text = payload["system"] + "\n" + payload["user"]
        row[mode] = [f"{who}: {what}" for who, what in LINE.findall(text)]
    result[f"c{label}"] = row
    print(f"c{label} {command!r}: gate_off={len(row['gate_off'])} gate_on={len(row['gate_on'])}")
    for line in row["gate_off"]:
        print("   ", "KEPT   " if line in row["gate_on"] else "REMOVED", line[:150])
kn.is_narrated = real
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
