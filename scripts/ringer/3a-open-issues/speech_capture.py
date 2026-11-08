# ruff: noqa: E501
"""Amendment 20, free step: capture speech-template arms on the kept P state at c4, c5, c9. Zero model calls.

S = current working tree (presence + P1, frame kept, new speaker-line template).
C = the same payload with the old template restored; c4 and c5 are asserted byte-equal to the Amendment 19 arm P payloads.
Run from the repo root: TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/3a-open-issues/speech_capture.py
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
LOC = ROOT / "bench/results/richer-3a-probe/loc"
OUT = ROOT / "bench/results/richer-3a-probe/speech"
NEW, OLD = " may talk about this fact: ", " may say this aloud: "

from bench.frozen_prompts import _write_json, capture  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)
capture(ROOT / "bench/variations/richer-3a-loc-P.json", [4, 5, 9], OUT / "frozen-S.json")
s = json.loads((OUT / "frozen-S.json").read_text())
c = copy.deepcopy(s)
p = json.loads((LOC / "frozen-P.json").read_text())
for ep in c["endpoints"]:
    user = ep["wire_payload"]["user"]
    assert user.count(NEW) >= 1 and OLD not in user, f"c{ep['n']}: expected the new template only"
    ep["wire_payload"]["user"] = user.replace(NEW, OLD)
for arm_ep, ctl_ep in zip(s["endpoints"], c["endpoints"], strict=True):
    n = arm_ep["n"]
    assert arm_ep["wire_payload"]["system"] == ctl_ep["wire_payload"]["system"]
    print(
        f"c{n}: speaker lines {arm_ep['wire_payload']['user'].count(NEW)}; chars C/S {len(ctl_ep['wire_payload']['user'])}/{len(arm_ep['wire_payload']['user'])}"
    )
    if n in (4, 5):
        ref = next(e for e in p["endpoints"] if e["n"] == n)
        assert ctl_ep["wire_payload"]["user"] == ref["wire_payload"]["user"], (
            f"c{n}: derived control differs from the Amendment 19 P payload"
        )
        assert ctl_ep["wire_payload"]["system"] == ref["wire_payload"]["system"]
        assert ctl_ep["committed_after_prefix"] == ref["committed_after_prefix"]
        print(f"c{n}: derived control == Amendment 19 P payload byte for byte")
_write_json(OUT / "frozen-C.json", c)
print("hashes", *[__import__("hashlib").sha256((OUT / f"frozen-{a}.json").read_bytes()).hexdigest()[:12] for a in "CS"])
# the c9 state, for the prereg
for ep in s["endpoints"]:
    print(ep["n"], ep["command"], "| committed:", len(ep["committed_after_prefix"]))
