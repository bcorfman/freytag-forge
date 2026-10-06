"""Count recorded L2 commands that match each reveal's evidence groups (requires ignored).

usage: reveal_coverage.py <e2e-blind-player.json>
"""

import json
import sys
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

D = Path("data/stories/continuity-initiative")
K = yaml.safe_load((D / "knowledge.yaml").read_text())["knowledge"]
RUN = Path(sys.argv[1])
r = json.loads(RUN.read_text())
for sc in ("1B", "1C", "2A", "2B", "2C", "3A", "3B"):
    cmds = [t["input"] for rep in r["replicates"] for s in rep["scenes"] if s["scene"] == sc for t in s["turns"]]
    items = [k for k in K if k["id"].startswith("k_sl_" + sc.lower() + "_") and k.get("action_evidence")]
    print(f"== {sc}: {len(cmds)} commands")
    for k in items:
        ev = tuple(tuple(g) for g in k["action_evidence"])
        hits = [c for c in cmds if _matches_all(ev, c)]
        print(f"  {k['id']}: {len(hits)} match", ("| e.g. " + hits[0][:60]) if hits else "")
