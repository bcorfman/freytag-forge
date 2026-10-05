"""Score the 1B reveal groups in knowledge.yaml with the real matcher."""

import sys
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
items = K["knowledge"] if isinstance(K, dict) and "knowledge" in K else K
G = {}
for it in items if isinstance(items, list) else []:
    if str(it.get("id", "")).startswith("k_sl_1b_"):
        G[it["id"].removeprefix("k_sl_1b_")] = tuple(tuple(g) for g in it.get("action_evidence", []))
assert {"a_r1", "a_r2", "b_r1", "b_r2", "c_r1", "c_r2"} <= set(G), sorted(G)

# command -> the one reveal expected (None = none of the step's reveals)
CASES = {
    "Show the man Michelle's photograph.": "b_r1",
    "Show the photograph to the man.": "b_r1",
    "Hold up the photograph to the watcher.": "b_r1",
    "Ask the man about the photograph.": "b_r1",
    "Question the man about Michelle's photograph.": "b_r1",
    "Approach the man with the photograph.": "b_r1",
    "Confront the stranger with the photo.": "b_r1",
    "Show him the photograph.": "b_r1",
    "Hand the man the photograph.": "b_r1",
    "Give the man the photograph.": "b_r1",
    "Show the watcher Michelle's photo.": "b_r1",
    "Ask the stranger about the photograph.": "b_r1",
    "Question the man about Michelle.": "b_r2",
    "Ask the watcher about Michelle.": "b_r2",
    "Press the man about Michelle.": "b_r2",
    "Ask him about Michelle.": "b_r2",
    "Talk to the man about Michelle.": "b_r2",
    "Examine the photograph.": "a_r2",
    "Compare the token to the number sequence.": "a_r1",
    "Question the man.": None,
    "Approach the watcher.": None,
    "Search the bench.": None,
    "Examine the man.": None,
    "Inspect the service path.": None,
    "Question the stranger.": None,
    "Follow Brandon through the maintenance gate.": "c_r1",
    "Follow Brandon into the storm drain.": "c_r1",
    "Go through the gate.": "c_r1",
    "Enter the storm drain.": "c_r1",
    "Run through the gate with Brandon.": "c_r1",
    "Head into the tunnel.": "c_r1",
    "Take the tunnel.": "c_r1",
    "Enter the drain.": "c_r1",
    "Enter the tunnel.": "c_r1",
    "Go through the storm drain.": "c_r1",
    "Go into the storm drain.": "c_r1",
    "Climb into the storm drain.": "c_r1",
    "Flee through the gate.": "c_r1",
    "Escape through the storm drain.": "c_r1",
    "Follow Brandon through the secured gate.": "c_r1",
    "Follow Brandon.": "c_r1",
    "Ask Brandon to use the gate code.": "c_r2",
    "Tell Brandon to open the gate with the code.": "c_r2",
    "Ask Brandon for the gate code.": "c_r2",
    "Ask Brandon to open the gate.": "c_r2",
    "Ask Brandon to unlock the gate.": "c_r2",
    "Tell Brandon to use the code.": "c_r2",
    "Search the storm drain.": None,
    "Examine the gate.": None,
    "Look into the tunnel.": None,
    "Search the maintenance gate.": None,
    "Inspect the drain.": None,
}
bad = 0
for cmd, want in CASES.items():
    step = want[0] if want else ("c" if any(w in cmd.lower() for w in ("gate", "drain", "tunnel", "brandon")) else "b")
    pool = [k for k in G if k[0] in (step, "a")] if step != "c" else [k for k in G if k[0] == "c"]
    got = [k for k in pool if _matches_all(G[k], cmd)]
    ok = got == ([want] if want else [])
    if not ok:
        bad += 1
        print(f"FAIL {cmd!r}: expected {want}, matched {got}")
if bad:
    sys.exit(1)
print(f"1B wording ok: {len(CASES)} commands")
