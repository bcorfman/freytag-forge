"""Compare blind-player runs by profile from saved merged reports (read-only, no network).

usage: profile_compare.py <canonical_dir> <raw_dir>
"""

import json
import sys
from collections import Counter
from pathlib import Path


def turns(report):
    for rep in report["replicates"]:
        for sc in rep["scenes"]:
            for t in sc.get("turns", []):
                yield rep["replicate"], sc["scene"], t


def bundles(directory):
    for p in sorted(Path(directory).glob("e2e-blind-player-bundles-r*.json")):
        for rep in json.loads(p.read_text())["replicates"]:
            for sc in rep["scenes"]:
                for b in sc["bundles"]:
                    yield sc["scene"], b["attempt_bundle"]


def summarise(directory):
    report = json.loads((Path(directory) / "e2e-blind-player.json").read_text())
    out = {"turns": 0, "rejected": 0, "reveals": Counter(), "exits": Counter(), "outcomes": Counter(), "universe5": 0}
    scene_turns = Counter()
    for _rep, scene, t in turns(report):
        out["turns"] += 1
        scene_turns[scene] += 1
    for scene, a in bundles(directory):
        if a.get("rejection"):
            out["rejected"] += 1
        out["reveals"][scene] += len(a["selected_reveal"]["knowledge_ids"])
        if a.get("transition_cause") not in (None, "none"):
            out["exits"][(scene, a["transition_cause"])] += 1
        rs = a.get("reveal_selection") or {}
        out["outcomes"][rs.get("outcome")] += 1
        if rs.get("universe_size", 0) >= 5:
            out["universe5"] += 1
    out["scene_turns"] = scene_turns
    return out


if __name__ == "__main__":
    for label, d in zip(("canonical", "raw"), sys.argv[1:3]):
        s = summarise(d)
        print(f"== {label}: {s['turns']} turns, {s['rejected']} rejected, universe>=5 on {s['universe5']}")
        print("  turns per scene:", dict(sorted(s["scene_turns"].items())))
        print("  reveals selected per scene:", dict(sorted(s["reveals"].items())))
        print("  exits:", dict(sorted(s["exits"].items())))
        print("  reveal_selection outcomes:", dict(s["outcomes"]))
