# ruff: noqa: E501
"""Experiment GUE (stage 2): GU2 plus the embrace delivery text, captured from the REAL engine in the working tree. Zero model calls.
Template = frozen-GU2.json (settings, transport). Asserts the system text, settings, command, committed facts and every speaker line are identical to GU2;
reports every other changed line (they must be the earlier-in-the-story lines that carry the new reunion delivery text).
Run: TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/gue_capture.py"""

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
from bench.core import load_variation  # noqa: E402

OUT = ROOT / "bench/results/shared-narrator/g"
gu2 = json.loads((OUT / "frozen-GU2.json").read_text())
gue = copy.deepcopy(gu2)
fp.SCENE = "3A"
variation = load_variation(ROOT / "bench/variations/richer-3a-loc-P.json")
fp._script_inputs(variation)
states, inputs = fp._prefix_states(variation, [4, 5, 9])
for ep_old, ep_new in zip(gu2["endpoints"], gue["endpoints"], strict=True):
    n = ep_old["n"]
    payload, _ = fp._capture_wire_payload(copy.deepcopy(states[n - 1]), inputs[n - 1])
    old = ep_old["wire_payload"]
    assert payload["system"] == old["system"] and payload["max_tokens"] == old["max_tokens"]
    assert payload["response_format"] == old["response_format"] and inputs[n - 1] == ep_old["command"]
    a, b = old["user"].split("\n"), payload["user"].split("\n")
    speaker = lambda lines: [x for x in lines if " may say this aloud: " in x]  # noqa: E731
    assert speaker(a) == speaker(b), f"c{n}: speaker lines differ"
    only_new = [x for x in b if x not in a]
    only_old = [x for x in a if x not in b]
    print(
        f"c{n}: user chars GU2/GUE {len(old['user'])}/{len(payload['user'])}; lines only in GU2: {len(only_old)}, only in GUE: {len(only_new)}"
    )
    for line in only_old:
        print("   GU2 only:", line[:230])
    for line in only_new:
        print("   GUE only:", line[:230])
    ep_new["wire_payload"] = payload
path = OUT / "frozen-GUE.json"
path.write_text(json.dumps(gue, ensure_ascii=False, indent=2) + "\n")
print("GUE", hashlib.sha256(path.read_bytes()).hexdigest()[:12])
