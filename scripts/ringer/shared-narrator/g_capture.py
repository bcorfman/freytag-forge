# ruff: noqa: E501
"""Experiment G (narrated-prerequisite gate, then the shared first-person sentence), free step. Zero model calls.

Arms at 3A c4, c5, c9 on the kept P state:
  C0 = gate off (every sibling realization still sayable; the production behaviour before the gate),
  G  = gate on (only narrated entries are offered as speaker lines),
  GF = G plus one sentence in the SYSTEM message, directly after "Do not copy sentences from the SCENE section.".
Asserts every allowed-line difference. Writes bench/results/shared-narrator/g/frozen-{C0,G,GF}.json.

Run from the repo root:
TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/g_capture.py
"""

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
import storygame.runtime.knowledge as kn  # noqa: E402
from bench.core import load_variation  # noqa: E402

TEMPLATE = ROOT / "bench/results/richer-3a-probe/speech/frozen-C.json"
OUT = ROOT / "bench/results/shared-narrator/g"
OUT.mkdir(parents=True, exist_ok=True)
ANCHOR = "Do not copy sentences from the SCENE section."
FIRST_PERSON = (
    "When a person speaks about themselves, use first person. Keep another person's words unchanged when quoting them."
)
PREFIX = " may say this aloud: "

fp.SCENE = "3A"
variation = load_variation(ROOT / "bench/variations/richer-3a-loc-P.json")
fp._script_inputs(variation)
states, inputs = fp._prefix_states(variation, [4, 5, 9])
real = kn.is_narrated
template = json.loads(TEMPLATE.read_text())
arms = {name: copy.deepcopy(template) for name in ("C0", "G", "GF")}
report = {}
for ep_c0, ep_g, ep_gf in zip(arms["C0"]["endpoints"], arms["G"]["endpoints"], arms["GF"]["endpoints"], strict=True):
    n = ep_c0["n"]
    command = inputs[n - 1]
    assert command == ep_c0["command"], (n, command, ep_c0["command"])
    payloads = {}
    for mode in ("off", "on"):
        kn.is_narrated = real if mode == "on" else (lambda item, facts: True)
        payloads[mode], _ = fp._capture_wire_payload(copy.deepcopy(states[n - 1]), command)
    kn.is_narrated = real
    off, on = payloads["off"], payloads["on"]
    old = ep_c0["wire_payload"]
    # C0 must equal the saved Amendment 20 control byte for byte; if not, the working tree has drifted.
    same_system, same_user = off["system"] == old["system"], off["user"] == old["user"]
    # Gate arm: identical except for speaker lines that disappear (each removed line existed in C0, order kept).
    assert on["system"] == off["system"] and on["max_tokens"] == off["max_tokens"]
    assert on["response_format"] == off["response_format"]
    off_lines, on_lines = off["user"].split("\n"), on["user"].split("\n")
    it = iter(off_lines)
    assert all(line in it for line in on_lines), f"c{n}: gate arm is not a subsequence of the control"
    removed = [line for line in off_lines if line not in on_lines]
    assert all(PREFIX in line for line in removed), f"c{n}: a removed line is not a speaker line: {removed}"
    # First-person arm: one inserted sentence in the system message, user identical to G.
    assert off["system"].count(ANCHOR) == 1, f"c{n}: anchor count {off['system'].count(ANCHOR)}"
    gf = copy.deepcopy(on)
    gf["system"] = on["system"].replace(ANCHOR, ANCHOR + " " + FIRST_PERSON)
    assert gf["system"].replace(" " + FIRST_PERSON, "") == on["system"] and gf["user"] == on["user"]
    ep_c0["wire_payload"], ep_g["wire_payload"], ep_gf["wire_payload"] = off, on, gf
    report[f"c{n}"] = {
        "command": command,
        "c0_equals_saved_control": {"system": same_system, "user": same_user},
        "speaker_lines_c0_g": [sum(PREFIX in x for x in off_lines), sum(PREFIX in x for x in on_lines)],
        "removed": [x[:140] for x in removed],
        "chars_user_c0_g_gf": [len(off["user"]), len(on["user"]), len(gf["user"])],
        "chars_system_c0_g_gf": [len(off["system"]), len(on["system"]), len(gf["system"])],
    }
    print(
        f"c{n} {command!r}: C0==saved control system={same_system} user={same_user}; lines {report[f'c{n}']['speaker_lines_c0_g']}"
    )
    for line in removed:
        print("   removed:", line[:140])
for name, value in arms.items():
    path = OUT / f"frozen-{name}.json"
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(name, hashlib.sha256(path.read_bytes()).hexdigest()[:12])
(OUT / "capture-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
