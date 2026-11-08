# ruff: noqa: E501
"""Experiment GU2 (gate + speaker lines rewritten so a speaker never retells Kristin her own action), free step. Zero model calls.
GU = the gate payloads of experiment G (bench/results/shared-narrator/g/frozen-G.json) with the speaker-line text replaced, per speaker,
by the authored utterance below. Every other byte identical (asserted). No prompt sentence is added: the person is written into the source.
Run: TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/gu_capture.py"""

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "bench/results/shared-narrator/g/frozen-G.json"
OUT = ROOT / "bench/results/shared-narrator/g"
PREFIX = " may say this aloud: "
MICHELLE, BRANDON, OFFICIAL = "Dr. Michelle McGehee", "Brandon Corfman", "Imprisoned senior official"

A_R1 = "Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements."
B_R2 = "Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments."
D_R1 = "The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority."
C_R1 = "Michelle hands Kristin the stolen radio and Kristin gives the signal; prisoners seize checkpoints and open a fighting route toward the command and broadcast levels."
ORG_M = "I've been organizing everyone with secret announcements over our stolen radios."
ORG_O = "Dr. McGehee's been organizing everyone with secret announcements over the stolen radios."
MED = "The medical level is where they ran memory, compliance, and resistance experiments on the prisoners."
AUTH = "That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority."
SIGNAL = (
    "The prisoners have the checkpoints, and they're fighting their way up toward the command and broadcast levels."
)
OVERRIDE = {
    (MICHELLE, A_R1): ORG_M,
    (BRANDON, A_R1): ORG_O,
    (OFFICIAL, A_R1): ORG_O,
    (MICHELLE, B_R2): MED,
    (BRANDON, B_R2): MED,
    (OFFICIAL, B_R2): MED,
    (MICHELLE, D_R1): AUTH,
    (BRANDON, D_R1): AUTH,
    (OFFICIAL, D_R1): AUTH,
    (MICHELLE, C_R1): f"Your signal worked. {SIGNAL}",
    (BRANDON, C_R1): f"The signal worked. {SIGNAL}",
    (OFFICIAL, C_R1): f"The signal worked. {SIGNAL}",
}
EXPECTED_REPLACED = {
    4: 3,
    5: 6,
    9: 12,
}  # c9 keeps the three "The uprising is active ..." lines unchanged (no self-reference)

g = json.loads(SRC.read_text())
gu = copy.deepcopy(g)
for ep in gu["endpoints"]:
    lines, replaced = ep["wire_payload"]["user"].split("\n"), 0
    for i, line in enumerate(lines):
        if PREFIX in line and line.startswith("- "):
            speaker, statement = line[2:].split(PREFIX, 1)
            new = OVERRIDE.get((speaker, statement))
            if new is not None:
                lines[i] = f"- {speaker}{PREFIX}{new}"
                replaced += 1
    ep["wire_payload"]["user"] = "\n".join(lines)
    assert replaced == EXPECTED_REPLACED[ep["n"]], (ep["n"], replaced)
for eg, eu in zip(g["endpoints"], gu["endpoints"], strict=True):
    assert eg["wire_payload"]["system"] == eu["wire_payload"]["system"] and eg["command"] == eu["command"]
    gl, ul = eg["wire_payload"]["user"].split("\n"), eu["wire_payload"]["user"].split("\n")
    assert len(gl) == len(ul) and all(a == b or PREFIX in a for a, b in zip(gl, ul, strict=True))
    print(
        f"c{eg['n']}: replaced {EXPECTED_REPLACED[eg['n']]} speaker lines; user chars G/GU {len(eg['wire_payload']['user'])}/{len(eu['wire_payload']['user'])}"
    )
    for line in ul:
        if PREFIX in line:
            print("   ", line[2:][:170])
path = OUT / "frozen-GU2.json"
path.write_text(json.dumps(gu, ensure_ascii=False, indent=2) + "\n")
print("GU", hashlib.sha256(path.read_bytes()).hexdigest()[:12])
