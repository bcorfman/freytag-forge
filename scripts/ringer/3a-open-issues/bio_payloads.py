# ruff: noqa: E501
"""Build the per-endpoint frozen payloads for the Kristin-bio arm (offline, zero neurons).

Stage A: the trimmed-A-r1 payloads saved by Amendment 12 (old bio) and the same payloads with only Kristin's CHARACTERS line swapped to the new bio.
Stage B: the two captures of the current D1 package (old bio frozen copy, new bio live), split per endpoint.
"""

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A1 = ROOT / "bench/results/richer-3a-probe/a1"
BIO = ROOT / "bench/results/richer-3a-probe/bio"
GOAL = " She wants to find her best friend, Michelle."


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.name, hashlib.sha256(path.read_bytes()).hexdigest()[:12])


def split(src: Path, n: int, dst: Path) -> dict:
    data = json.loads(src.read_text(encoding="utf-8"))
    data["endpoints"] = [e for e in data["endpoints"] if e["n"] == n]
    assert len(data["endpoints"]) == 1
    write(dst, data)
    return data


for n in (4, 5):
    old = json.loads((A1 / f"frozen-candidate-c{n}.json").read_text(encoding="utf-8"))
    new = copy.deepcopy(old)
    user_old = old["endpoints"][0]["wire_payload"]["user"]
    lines = user_old.splitlines(keepends=True)
    hits = [
        i
        for i, line in enumerate(lines)
        if line.startswith("- Kristin Schweitzer is ") and line.rstrip("\n").endswith(GOAL)
    ]
    assert len(hits) == 1, hits
    lines[hits[0]] = lines[hits[0]].replace(GOAL, "", 1)
    new["endpoints"][0]["wire_payload"]["user"] = "".join(lines)
    assert len(user_old) - len(new["endpoints"][0]["wire_payload"]["user"]) == len(GOAL)
    write(BIO / f"frozen-trim-old-c{n}.json", old)
    write(BIO / f"frozen-trim-new-c{n}.json", new)
    for arm in ("control", "candidate"):
        split(BIO / f"frozen-{arm}.json", n, BIO / f"frozen-{arm}-c{n}.json")
