"""Print a compact digest of an L1 or L2 report: rates first, detail only for misses.

Usage: python3 scripts/ringer/affordance/digest.py artifacts/e2e-affordances.json
       python3 scripts/ringer/affordance/digest.py artifacts/e2e-blind-player.json
"""

import json
import sys


def l1(report):
    rows = {}
    for rep, scene in enumerate(report["scenes"], 1):
        for kind in ("first_step", "later"):
            for a in scene.get(kind, []):
                key = (scene["scene_id"], kind, a["name"])
                rows.setdefault(key, {})[rep] = a
    reps = len(report["scenes"])
    print(f"L1: {reps} scene-replicates (turn 0 = opening; deadline = turn 0 or 1)")
    print(f"{'scene':<5} {'kind':<10} {'affordance':<32} " + " ".join(f"r{i}".ljust(6) for i in range(1, reps + 1)))
    for (scene, kind, name), by_rep in rows.items():
        cells = []
        for i in range(1, reps + 1):
            a = by_rep.get(i)
            t = "?" if a is None else ("NEVER" if a["first_shown_turn"] is None else str(a["first_shown_turn"]))
            cells.append(t.ljust(6))
        print(f"{scene:<5} {kind:<10} {name[:32]:<32} " + " ".join(cells))
    for rep, scene in enumerate(report["scenes"], 1):
        s = scene["summary"]
        print(
            f"r{rep} {scene['scene_id']}: by deadline {s['shown_by_deadline']}/{s['first_step_total']}, "
            f"never shown {s['never_shown']}, input {scene.get('input')!r}"
        )


def l2(report):
    agg = report.get("aggregate", {})
    print("L2 aggregate:", json.dumps(agg, indent=None))
    for rep, run in enumerate(report.get("replicates", []), 1):
        shown = ", ".join(f"{a['entity_id']}@{a['first_shown_turn']}" for a in run.get("affordances", []))
        print(
            f"r{rep}: transition={run.get('transition_fired')} turn={run.get('transition_turn')} "
            f"stuck_turns={run.get('stuck_turns')} stuck_runs={len(run.get('stuck_runs', []))} "
            f"silent={run.get('silent_transition')}"
        )
        print(f"    shown: {shown}")
        for sr in run.get("stuck_runs", []):
            print("    STUCK RUN:", json.dumps(sr)[:300])
        l3 = run.get("l3") or {}
        print("    l3:", json.dumps(l3)[:300])


with open(sys.argv[1]) as handle:
    report = json.load(handle)
(l2 if "replicates" in report else l1)(report)
