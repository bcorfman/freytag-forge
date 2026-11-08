# ruff: noqa: E501
"""Experiment GUE1 scoring: blind scores (written from the shuffled sheet) joined with the key. Prints counts per endpoint and arm.
P = PRE (the lead-up already performs the embrace or reunion moment), D = DUP (restates the appended content), E = EXTRA (a character other than Kristin speaks, or an unrequested act or find),
C = CONTRA (contradicts the appended text), F = composed turn not coherent (Michelle's answer in the lead-up, then the appended answer), V = DIV (lead-up goes to someone other than Michelle; recorded),
Y = EYE (an eye-contact or emotion look; recorded, not PRE)."""

import json
from collections import Counter
from pathlib import Path

D = Path("bench/results/shared-narrator/g")
R1 = {
    1: "VE",
    2: "VE",
    4: "V",
    6: "",
    7: "Y",
    9: "V",
    13: "V",
    16: "V",
    17: "",
    19: "V",
    20: "V",
    26: "",
    27: "V",
    29: "V",
    31: "VE",
    32: "",
    33: "V",
    35: "P",
    38: "V",
    40: "V",
    41: "V",
    43: "V",
    45: "VE",
    47: "V",
}
R2 = {
    3: "EDF",
    5: "ECF",
    8: "",
    10: "",
    11: "ECF",
    12: "EDF",
    14: "Y",
    15: "EDF",
    18: "",
    21: "",
    22: "",
    23: "Y",
    24: "EDF",
    25: "",
    28: "ECF",
    30: "EDF",
    34: "",
    36: "EDF",
    37: "EDF",
    39: "EDF",
    42: "ECF",
    44: "",
    46: "",
    48: "",
}
SCORES = {"R1": R1, "R2": R2}
(D / "scores-gue1-blind.json").write_text(
    json.dumps({n: {str(k): v for k, v in s.items()} for n, s in SCORES.items()}, indent=1)
)
key = json.loads((D / "key-GUE1.json").read_text())
counts, seen = {}, Counter()
for k in key:
    cell = (k["n"], k["arm"])
    seen[cell] += 1
    counts.setdefault(cell, Counter())
    for f in SCORES[k["n"]][k["sheet"]]:
        counts[cell][f] += 1
    assert k["mechanical_ok"], k
for cell in sorted(counts):
    print(f"{cell[0]} {cell[1]:3} n={seen[cell]} " + " ".join(f"{f}={c}" for f, c in sorted(counts[cell].items())))
