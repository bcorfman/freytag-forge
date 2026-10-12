"""Score hosted blind-player batches for scenes 1A-1C.

usage: weak1c_compare.py <label>=<dir-with-batch*/e2e-blind-player.json> ...
Counts per arm: replicates, scene exit cause, rejected turns, and for 1C the turn on
which each of k_sl_1c_b_r1 and k_sl_1c_b_r2 was earned (grounding_ids on a turn).
"""

import json
import sys
from pathlib import Path

B_IDS = ("k_sl_1c_b_r1", "k_sl_1c_b_r2")


def load(directory):
    for path in sorted(Path(directory).glob("batch*/e2e-blind-player.json")):
        yield from json.loads(path.read_text())["replicates"]


def score(directory):
    out = {"reps": 0, "scenes": {}, "rejected": [], "b_turns": [], "b_missing": 0, "photo_rejections": 0}
    for rep in load(directory):
        out["reps"] += 1
        for scene in rep["scenes"]:
            tally = out["scenes"].setdefault(scene["scene"], {"play": 0, "forced": 0, "none": 0})
            cause = scene["exit_cause"]
            tally["play" if cause == "play" else "forced" if cause in ("forced", "timer") else "none"] += 1
            for turn in scene["turns"]:
                if turn["rejected"]:
                    out["rejected"].append((scene["scene"], turn["raw_input"], str(turn["rejection"])[:80]))
                    if "photo" in str(turn["rejection"]):
                        out["photo_rejections"] += 1
            if scene["scene"] == "1C":
                hits = [t["turn"] for t in scene["turns"] if any(i in (t.get("grounding_ids") or []) for i in B_IDS)]
                if hits:
                    out["b_turns"].append(min(hits))
                else:
                    out["b_missing"] += 1
    return out


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        label, directory = arg.split("=", 1)
        s = score(directory)
        print(f"== {label}: {s['reps']} replicates")
        for scene, tally in s["scenes"].items():
            print(f"  {scene}: by play {tally['play']}, forced {tally['forced']}, other {tally['none']}")
        b = sorted(s["b_turns"])
        print(f"  1C b-reveal earned in {len(b)} of {len(b) + s['b_missing']} replicates; turns {b}")
        print(f"  rejected turns {len(s['rejected'])} (photo-related {s['photo_rejections']})")
        for item in s["rejected"]:
            print("    ", item)
