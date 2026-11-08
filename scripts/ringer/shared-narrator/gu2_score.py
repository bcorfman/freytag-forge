# ruff: noqa: E501
"""Experiment GU2 scoring: blind scores (written from the shuffled sheet) joined with the key. Prints counts per endpoint.
c4: I command, H third-person recital, D unquoted third-person self-reference, P plans instead, E malformed, R authored line voiced.
c5: J question asked and attributed (strict), K premature answer or invented memory, P plan exchange, H recital.
c9: 1 handover or signal again, U the unchanged 'uprising is active' line voiced, A authorization voiced, 3 answers command, 4 radio conflict, M malformed, R authored line voiced."""

import json
from collections import Counter
from pathlib import Path

D = Path("bench/results/shared-narrator/g")
C4 = {3: "R", 6: "R", 7: "R", 8: "R", 14: "RE", 20: "R", 23: "R", 25: "R", 28: "RHP", 29: "R", 35: "R", 36: "R"}
C5 = {1: "J", 2: "J", 4: "J", 10: "PH", 12: "PH", 13: "", 16: "", 18: "P", 19: "", 22: "J", 24: "PH", 34: "J"}
C9 = {
    5: "U3",
    9: "U3",
    11: "U3M",
    15: "U3",
    17: "U",
    21: "U3",
    26: "U3",
    27: "U3",
    30: "U3M",
    31: "U3",
    32: "U",
    33: "U3MA",
}
SCORES = {4: C4, 5: C5, 9: C9}
(D / "scores-gu2-blind.json").write_text(
    json.dumps({str(n): {str(k): v for k, v in s.items()} for n, s in SCORES.items()}, indent=1)
)
key = json.loads((D / "key-GU2.json").read_text())
counts = {n: Counter() for n in (4, 5, 9)}
seen = Counter()
mech = Counter()
for k in key:
    seen[k["n"]] += 1
    mech[k["n"]] += not k["mechanical_ok"]
    for f in SCORES[k["n"]][k["sheet"]]:
        counts[k["n"]][f] += 1
for n in (4, 5, 9):
    print(
        f"c{n} n={seen[n]} mechanical_failures={mech[n]} " + " ".join(f"{f}={c}" for f, c in sorted(counts[n].items()))
    )
