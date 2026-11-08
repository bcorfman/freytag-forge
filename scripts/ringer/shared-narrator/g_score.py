# ruff: noqa: E501
"""Experiment G scoring: blind scores (written before the key was opened) joined with the key. Prints per-arm counts."""

import json
from collections import defaultdict
from pathlib import Path

D = Path("bench/results/shared-narrator/g")
C4 = {
    1: "I",
    3: "HP",
    9: "P",
    18: "P",
    22: "HP",
    30: "I",
    33: "",
    34: "I",
    37: "I",
    38: "I",
    44: "I",
    45: "HP",
    46: "HP",
    47: "HD",
    49: "I",
    50: "HP",
    53: "HP",
    54: "HP",
    56: "I",
    58: "P",
    63: "HP",
    65: "HD",
    66: "I",
    67: "HD",
    73: "P",
    76: "",
    80: "P",
    83: "HP",
    84: "P",
    86: "I",
    88: "HD",
    94: "IE",
    96: "F",
    103: "P",
    104: "HP",
    108: "P",
}
C5 = {
    2: "JK",
    4: "",
    5: "P",
    6: "K",
    8: "",
    14: "",
    16: "",
    19: "",
    21: "",
    23: "",
    26: "J",
    27: "",
    29: "",
    31: "",
    32: "J",
    35: "J",
    41: "",
    48: "K",
    52: "",
    55: "K",
    59: "K",
    62: "",
    68: "",
    69: "K",
    74: "",
    75: "",
    77: "JK",
    85: "K",
    90: "",
    93: "J",
    97: "",
    98: "",
    99: "J",
    100: "JKPH",
    106: "J",
    107: "",
}
C9 = {
    7: "35",
    10: "13",
    11: "13",
    12: "3",
    13: "13",
    15: "123",
    17: "123",
    20: "35",
    24: "3",
    25: "13",
    28: "123",
    36: "13",
    39: "123",
    40: "123",
    42: "123",
    43: "13",
    51: "13",
    57: "14",
    60: "13",
    61: "3",
    64: "3",
    70: "13",
    71: "123",
    72: "13",
    78: "13",
    79: "123",
    81: "13",
    82: "3",
    87: "13",
    89: "13",
    91: "134",
    92: "14",
    95: "14",
    101: "3",
    102: "134",
    105: "123",
}
SCORES = {4: C4, 5: C5, 9: C9}
(D / "scores-blind.json").write_text(
    json.dumps({str(n): {str(k): v for k, v in s.items()} for n, s in SCORES.items()}, indent=1)
)
key = json.loads((D / "key-G.json").read_text())
counts = defaultdict(lambda: defaultdict(int))
seen = defaultdict(int)
for k in key:
    flags = SCORES[k["n"]][k["sheet"]]
    seen[(k["n"], k["arm"])] += 1
    for f in flags:
        counts[(k["n"], k["arm"])][f] += 1
for n in (4, 5, 9):
    for arm in ("C0", "G", "GF"):
        c = counts[(n, arm)]
        print(f"c{n} {arm:2} n={seen[(n, arm)]} " + " ".join(f"{f}={c[f]}" for f in sorted(c)))
