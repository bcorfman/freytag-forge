# ruff: noqa: E501
"""Experiment GU scoring: blind scores (written from the shuffled sheet) joined with the key. Prints counts per endpoint.
Flags c4: I command (medical level headed for), H third-person recital, D unquoted third-person self-reference, P plans instead, E malformed, R authored line voiced.
c5: J question asked and attributed (strict), K premature answer or invented memory, P plan exchange, H recital.
c9: 1 handover or signal again, 2 signal/statement voiced, 3 answers command, 4 radio custody conflict, 5 malformed (none), R authored line near-verbatim. B = borderline item 4 (Michelle shouts through 'the radio')."""

import json
from collections import Counter
from pathlib import Path

D = Path("bench/results/shared-narrator/g")
C4 = {4: "R", 5: "R", 7: "R", 8: "R", 13: "R", 17: "R", 21: "RE", 24: "R", 25: "HP", 26: "R", 27: "R", 33: "HP"}
C5 = {1: "", 3: "", 6: "J", 9: "P", 10: "", 12: "", 14: "P", 15: "J", 28: "", 30: "", 32: "", 36: "P"}
C9 = {
    2: "3",
    11: "3",
    16: "3",
    18: "3",
    19: "123RB",
    20: "123RB",
    22: "3",
    23: "123RB",
    29: "123RB",
    31: "3",
    34: "3",
    35: "123RB",
}
SCORES = {4: C4, 5: C5, 9: C9}
(D / "scores-gu-blind.json").write_text(
    json.dumps({str(n): {str(k): v for k, v in s.items()} for n, s in SCORES.items()}, indent=1)
)
key = json.loads((D / "key-GU.json").read_text())
counts = {n: Counter() for n in (4, 5, 9)}
seen = Counter()
for k in key:
    seen[k["n"]] += 1
    for f in SCORES[k["n"]][k["sheet"]]:
        counts[k["n"]][f] += 1
for n in (4, 5, 9):
    print(f"c{n} n={seen[n]} " + " ".join(f"{f}={c}" for f, c in sorted(counts[n].items())))
