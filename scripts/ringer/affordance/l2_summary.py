"""Summarise hosted L2 blind-player runs: exit type and rejected turns per scene across the given folders.

usage: l2_summary.py RUN_DIR [RUN_DIR ...]
Reads e2e-blind-player-r*.json (skips prompt files). Prints one row per scene and the rejected turns by phrase code.
"""

import glob
import json
import sys
from collections import Counter
from pathlib import Path

scenes: dict[str, list[str]] = {}
rejects: Counter[str] = Counter()
files = 0
for run_dir in sys.argv[1:]:
    for path in sorted(glob.glob(str(Path(run_dir) / "e2e-blind-player-r*.json"))):
        if "prompts" in path:
            continue
        report = json.loads(Path(path).read_text())
        files += 1
        for scene, block in report.get("by_scene", {}).items():
            if block.get("play_exit_rate"):
                exit_type = f"P{int(block.get('mean_transition_turn') or 0)}"
            elif block.get("timer_exit_rate"):
                exit_type = f"T{int(block.get('mean_transition_turn') or 0)}"
            elif block.get("transition_rate"):
                exit_type = "E"
            else:
                exit_type = "-"
            scenes.setdefault(scene, []).append(exit_type)
            if block.get("rejected_count"):
                rejects[scene] += int(block["rejected_count"])
print(f"{files} replicate files")
for scene in sorted(scenes):
    row = scenes[scene]
    plays = sum(1 for x in row if x.startswith("P"))
    timers = sum(1 for x in row if x.startswith("T"))
    exits = " ".join(row)
    print(f"{scene}: play {plays}/{len(row)}, timer {timers}/{len(row)}, rejected {rejects[scene]}  [{exits}]")
print("rejected turns total:", sum(rejects.values()))
