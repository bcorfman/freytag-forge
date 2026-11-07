"""Build the c4 payloads for the reunion-effect-under-the-new-bio arm (offline, zero neurons).

Control = the Amendment 13 stage B candidate capture (D1, new bio). Candidate = the saved Amendment 11 reunion-effect
c4 payload (old bio) with only Kristin's CHARACTERS line swapped to the new bio.
"""

import copy
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "bench/results/richer-3a-probe"
OUT = BASE / "reunion-bio"
GOAL = " She wants to find her best friend, Michelle."
OUT.mkdir(parents=True, exist_ok=True)


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.name, hashlib.sha256(path.read_bytes()).hexdigest()[:12])


control = json.loads((BASE / "bio/frozen-candidate-c4.json").read_text(encoding="utf-8"))
cand = copy.deepcopy(json.loads((BASE / "reunion/frozen-candidate-c4.json").read_text(encoding="utf-8")))
lines = cand["endpoints"][0]["wire_payload"]["user"].splitlines(keepends=True)
hits = [i for i, x in enumerate(lines) if x.startswith("- Kristin Schweitzer is ") and x.rstrip("\n").endswith(GOAL)]
assert len(hits) == 1
lines[hits[0]] = lines[hits[0]].replace(GOAL, "", 1)
cand["endpoints"][0]["wire_payload"]["user"] = "".join(lines)

cw, kw = control["endpoints"][0]["wire_payload"], cand["endpoints"][0]["wire_payload"]
assert cw["system"] == kw["system"]
assert {k: v for k, v in cw.items() if k != "user"} == {k: v for k, v in kw.items() if k != "user"}
diff = [
    d
    for d in difflib.unified_diff(cw["user"].splitlines(), kw["user"].splitlines(), lineterm="", n=0)
    if not d.startswith(("---", "+++", "@@"))
]
print("user", len(cw["user"]), "->", len(kw["user"]), "diff lines", len(diff))
for d in diff:
    print("  ", d[:170])
write(OUT / "frozen-control-c4.json", control)
write(OUT / "frozen-candidate-c4.json", cand)
