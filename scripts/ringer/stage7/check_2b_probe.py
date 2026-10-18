"""usage: check_2b_probe.py OUT_DIR N -- validate a 2B cue probe and recompute its hit counts from raw rows."""

import json
import sys
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

out, n = Path(sys.argv[1]), int(sys.argv[2])
ARMS = ["stage7-2b-cue-control", "stage7-2b-cue-b", "stage7-2b-cue-c"]
errs = []
try:
    rows = json.loads((out / "results.json").read_text())
    summary = json.loads((out / "summary.json").read_text())
except Exception as e:
    print(f"results.json/summary.json unreadable: {e}")
    sys.exit(1)

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text())["knowledge"]
G = {
    e["id"]: tuple(tuple(g) for g in e["action_evidence"])
    for e in K
    if "2B" in (e.get("available_in_scenes") or []) and e.get("action_evidence")
}
cue_words = {"stage7-2b-cue-b": "Michelle's file is one of them", "stage7-2b-cue-c": "One file carries Michelle's name"}
if len(rows) != 3 * n:
    errs.append(f"expected {3 * n} rows, found {len(rows)}")
recount = {a: 0 for a in ARMS}
for r in rows:
    for k in ("arm", "rep", "narration", "cue_visible", "command", "matched"):
        if k not in r:
            errs.append(f"row {r.get('arm')}/{r.get('rep')} lacks {k}")
    if r.get("arm") not in ARMS:
        errs.append(f"unknown arm {r.get('arm')}")
        continue
    got = sorted(i for i, g in G.items() if _matches_all(g, r.get("command", "")))
    if got != sorted(r.get("matched", [])):
        errs.append(f"{r['arm']} rep {r['rep']}: reported matched {r.get('matched')} but matcher says {got}")
    if got:
        recount[r["arm"]] += 1
    word = cue_words.get(r["arm"])
    if word and r.get("cue_visible") and word not in r.get("narration", ""):
        errs.append(f"{r['arm']} rep {r['rep']}: cue_visible true but cue text absent from narration")
for a in ARMS:
    if sum(1 for r in rows if r.get("arm") == a) != n:
        errs.append(f"arm {a} does not have {n} rows")
    if summary.get("arms", {}).get(a, {}).get("hits") != recount[a]:
        errs.append(f"summary hits for {a} = {summary.get('arms', {}).get(a, {}).get('hits')}, recount {recount[a]}")
cap = 3 * n
if summary.get("narration_calls", 0) > cap + 3 or summary.get("player_calls", 0) > 2 * cap:
    errs.append(f"call caps exceeded: {summary.get('narration_calls')} narration, {summary.get('player_calls')} player")
if errs:
    print("\n".join(errs))
    sys.exit(1)
print("probe valid; hits:", recount)
