"""Build the c4 payloads for the D1-V-under-the-new-bio arm (offline, zero neurons).

Control = the stage B candidate capture (D1 statements, new bio). Candidate = the saved D1-V c4 payload
(speaker lines removed, old bio) with only Kristin's CHARACTERS line swapped to the new bio.
"""

import copy
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BIO = ROOT / "bench/results/richer-3a-probe/bio"
OUT = ROOT / "bench/results/richer-3a-probe/d1v-bio"
GOAL = " She wants to find her best friend, Michelle."
OUT.mkdir(parents=True, exist_ok=True)


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.name, hashlib.sha256(path.read_bytes()).hexdigest()[:12])


control = json.loads((BIO / "frozen-candidate-c4.json").read_text(encoding="utf-8"))
d1v = json.loads((ROOT / "bench/results/richer-3a-probe/d1v/frozen-d1v.json").read_text(encoding="utf-8"))
d1v["endpoints"] = [e for e in d1v["endpoints"] if e["n"] == 4]
cand = copy.deepcopy(d1v)
lines = cand["endpoints"][0]["wire_payload"]["user"].splitlines(keepends=True)
hits = [i for i, x in enumerate(lines) if x.startswith("- Kristin Schweitzer is ") and x.rstrip("\n").endswith(GOAL)]
assert len(hits) == 1
lines[hits[0]] = lines[hits[0]].replace(GOAL, "", 1)
cand["endpoints"][0]["wire_payload"]["user"] = "".join(lines)

cw, kw = control["endpoints"][0]["wire_payload"], cand["endpoints"][0]["wire_payload"]
assert cw["system"] == kw["system"], "system differs"
assert {k: v for k, v in cw.items() if k != "user"} == {k: v for k, v in kw.items() if k != "user"}
a, b = cw["user"].splitlines(), kw["user"].splitlines()
diff = [d for d in difflib.unified_diff(a, b, lineterm="", n=0) if not d.startswith(("---", "+++", "@@"))]
removed = [d for d in diff if d.startswith("-")]
added = [d for d in diff if d.startswith("+")]
print("removed", len(removed), "added", len(added), "user", len(cw["user"]), "->", len(kw["user"]))
for d in removed:
    print("  ", d[:150])
assert len(removed) == 6 and not added
write(OUT / "frozen-control-c4.json", control)
write(OUT / "frozen-candidate-c4.json", cand)
