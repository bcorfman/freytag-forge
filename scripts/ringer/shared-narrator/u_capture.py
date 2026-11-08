# ruff: noqa: E501
"""Experiment U (authored speaker utterances), free step: derive the U arm from the saved speech control by substituting
speaker lines. Zero model calls. C = bench/results/richer-3a-probe/speech/frozen-C.json (old template, kept P state; c4, c5, c9).
U = the same payload with the override lines below; every other byte identical (asserted).
Run from the repo root: TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/u_capture.py"""

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "bench/results/richer-3a-probe/speech/frozen-C.json"
OUT = ROOT / "bench/results/shared-narrator/u"
OUT.mkdir(parents=True, exist_ok=True)
PREFIX = " may say this aloud: "
MICHELLE, BRANDON, OFFICIAL = "Dr. Michelle McGehee", "Brandon Corfman", "Imprisoned senior official"

A_R1 = "Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements."
A_R2 = "Michelle has explained that freeing this block means little without exposing the other sites."
B_R2 = "Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments."
D_R1 = "The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority."
D_R2 = "The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire."
OVERRIDE = {
    (MICHELLE, A_R1): "I'm coordinating the prisoners through stolen radios and coded announcements.",
    (BRANDON, A_R1): "Michelle is coordinating the prisoners through stolen radios and coded announcements.",
    (OFFICIAL, A_R1): "Dr. McGehee is coordinating the prisoners through stolen radios and coded announcements.",
    (MICHELLE, A_R2): "Freeing this block means little unless we expose the other sites.",
    (BRANDON, A_R2): "Freeing this block means little unless we expose the other sites.",
    (OFFICIAL, A_R2): "Freeing this block means little unless we expose the other sites.",
    (
        MICHELLE,
        B_R2,
    ): "I showed you the medical level, where prisoners were subjected to memory, compliance, and resistance experiments.",
    (
        OFFICIAL,
        D_R1,
    ): "I'm giving you one-use authorization for the emergency surface gates. It will expire when Charles activates his new authority.",
    (OFFICIAL, D_R2): "The authorization is real, but the one-use code is about to expire.",
}
# not overridden here (owned by the c9 replay work, O4): the two "Michelle hands Kristin the stolen radio ..." statements and "The uprising is active ..."
EXPECTED_REPLACED = {4: 6, 5: 7, 9: 9}

c = json.loads(SRC.read_text())
u = copy.deepcopy(c)
for ep in u["endpoints"]:
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
for ec, eu in zip(c["endpoints"], u["endpoints"], strict=True):
    assert ec["wire_payload"]["system"] == eu["wire_payload"]["system"] and ec["command"] == eu["command"]
    assert ec["committed_after_prefix"] == eu["committed_after_prefix"]
    cl, ul = ec["wire_payload"]["user"].split("\n"), eu["wire_payload"]["user"].split("\n")
    assert len(cl) == len(ul) and all(a == b or PREFIX in a for a, b in zip(cl, ul, strict=True))
    print(
        f"c{ec['n']}: replaced {EXPECTED_REPLACED[ec['n']]} speaker lines; user chars C/U {len(ec['wire_payload']['user'])}/{len(eu['wire_payload']['user'])}"
    )
for name, v in (("C", c), ("U", u)):
    (OUT / f"frozen-{name}.json").write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n")
    print(name, hashlib.sha256((OUT / f"frozen-{name}.json").read_bytes()).hexdigest()[:12])
