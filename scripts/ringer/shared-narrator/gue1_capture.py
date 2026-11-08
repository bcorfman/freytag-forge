# ruff: noqa: E501
"""Experiment GUE1 (stage 2, corrected): the embrace reaches the model only on the reunion turn itself, where CONSTRAINTS say
'Right after your story, the game will add this: <delivery_text>. Write only what leads up to it.' Zero model calls.
Endpoints: R1 = 'Free the captives.' (selects k_sl_3a_a_r1), R2 = 'Ask Michelle about the other sites.' (selects k_sl_3a_a_r2), both at the 3A entry state.
Arms: OLD = the previous delivery text (the real new payload with exactly that one line swapped back), EMB = the real engine payload with the embrace text.
Run: TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/gue1_capture.py"""

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
LEAD = "- Right after your story, the game will add this: "
OLD = {
    "R1": "Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. For one unhurried moment the two of them talk to each other and nobody asks anything of either. Then Michelle turns back to her coded announcements and points toward the medical level, where the experiment records wait.",
    "R2": "Michelle shares one unhurried moment with Kristin. She explains that freeing this block means little without exposing the other sites. Michelle points toward the medical level, where the experiment records wait.",
}
COMMANDS = {"R1": None, "R2": "Ask Michelle about the other sites."}

fp.SCENE = "3A"
variation = load_variation(ROOT / "bench/variations/richer-3a-loc-P.json")
inputs = fp._script_inputs(variation)
states, _ = fp._prefix_states(variation, [1, 2])
template = json.loads((OUT / "frozen-GU2.json").read_text())
frozen = {arm: {**template, "endpoints": []} for arm in ("OLD", "EMB")}
for key, command in COMMANDS.items():
    command = command or inputs[0]
    payload, _ = fp._capture_wire_payload(copy.deepcopy(states[0]), command)
    lines = payload["user"].split("\n")
    delivery_lines = [x for x in lines if x.startswith(LEAD)]
    assert len(delivery_lines) == 1, (key, command, len(delivery_lines))
    new_text = delivery_lines[0][len(LEAD) :]
    assert "embrace" in new_text and OLD[key] != new_text
    old_payload = copy.deepcopy(payload)
    old_payload["user"] = payload["user"].replace(LEAD + new_text, LEAD + OLD[key])
    a, b = old_payload["user"].split("\n"), payload["user"].split("\n")
    assert len(a) == len(b) and sum(x != y for x, y in zip(a, b, strict=True)) == 1
    for arm, wire in (("OLD", old_payload), ("EMB", payload)):
        frozen[arm]["endpoints"].append(
            {
                "n": key,
                "command": command,
                "prefix": [],
                "committed_after_prefix": [],
                "wire_payload": wire,
                "other_payloads": [],
            }
        )
    print(
        f"{key} {command!r}: user chars OLD/EMB {len(old_payload['user'])}/{len(payload['user'])}; system {len(payload['system'])}"
    )
    print("   EMB delivery:", new_text[:120], "...")
for arm, value in frozen.items():
    path = OUT / f"frozen-GUE1-{arm}.json"
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(arm, hashlib.sha256(path.read_bytes()).hexdigest()[:12])
