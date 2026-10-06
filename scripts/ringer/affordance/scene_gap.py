"""Per scene: bridge facts, the reveals that set them (with evidence groups), cues, and what a recorded L2 run did.

usage: scene_gap.py <scene> <e2e-blind-player.json>
"""

import json
import sys
from pathlib import Path

import yaml

D = Path("data/stories/continuity-initiative")
RUN = Path(sys.argv[2])
scene = sys.argv[1]
know = yaml.safe_load((D / "knowledge.yaml").read_text())
know = know["knowledge"]
routes = yaml.safe_load((D / "storylet-routes.yaml").read_text())
pac = yaml.safe_load((D / "pacing.yaml").read_text())
hand = yaml.safe_load((D / "handoffs.yaml").read_text())["deliveries"]
tr = [t for t in pac["transitions"] if t["source_scene_id"] == scene][0]
print("TRANSITION", tr["id"], [t["fact_id"] for t in tr["triggers"]], "deps", tr.get("required_dependencies"))


def setters(fact):
    return [
        k
        for k in know
        if isinstance(k, dict)
        and any((e or {}).get("fact_id") == fact for e in (k.get("establishes") or []) if isinstance(e, dict))
    ]


def show(k, ind="  "):
    ev = k.get("action_evidence")
    print(ind + k["id"], "| earn:", k.get("earn_when"))
    print(
        ind + "  requires",
        [r["fact_id"] for r in k.get("requires", [])],
        "establishes",
        [e["fact_id"] for e in k["establishes"] if isinstance(e, dict)],
    )
    if ev:
        print(ind + "  evidence", [g[:8] for g in ev] if len(json.dumps(ev)) > 600 else ev)
    print(ind + "  delivery:", (k.get("delivery_text") or "")[:260].replace("\n", " "))


seen = set()


def walk(fact, depth=0):
    for k in setters(fact):
        if k["id"] in seen:
            continue
        seen.add(k["id"])
        print("  " * depth + f"[{fact}] <-")
        show(k, "  " * depth + "  ")
        for r in k.get("requires", []):
            walk(r["fact_id"], depth + 1)


bridges = [b for b in routes["canonical_bridge_events"] if b["scene_id"] == scene]
roots = [t["fact_id"] for t in tr["triggers"]]
for b in bridges:
    act = b["activation"]
    print("BRIDGE", b["id"], act)
    roots = [f for key in ("all_facts_true", "any_of") for f in (act.get(key) or []) if isinstance(f, str)]
for f in roots:
    if not setters(f):
        print("  NO reveal sets", f)
    walk(f)
print("HANDOFFS")
for h in hand:
    if h["scene_id"] == scene:
        print(" ", h["fact_id"], "| cue:", h.get("cue_text"))
print("RUNS")
r = json.loads(RUN.read_text())
for rep in r["replicates"]:
    s = [x for x in rep["scenes"] if x["scene"] == scene][0]
    print(" r", rep["replicate"], s["exit_cause"], s["transition_turn"])
    print(
        "    "
        + " || ".join(
            f"{t['turn']} {t['input'][:55]}"
            + (f" [{','.join(t['grounding_ids'])}]" if t.get("grounding_ids") else "")
            + (" REJ" if t["rejected"] else "")
            for t in s["turns"]
        )
    )
