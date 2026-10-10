#!/bin/bash
# Ringer check: runs the 3C cue-gate probe and verifies its report has every stage and the expected keys.
set -u
OUT=/home/bcorfman/dev/ringer-work/3c-cue-gate
mkdir -p "$OUT"
cd /home/bcorfman/dev/freytag-forge || exit 1
uv run python scripts/ringer/affordance/3c_cue_gate_probe.py "$OUT/report.json" > "$OUT/stdout.txt" 2>"$OUT/stderr.txt" || { echo "FAIL: probe crashed"; tail -20 "$OUT/stderr.txt"; exit 1; }
uv run python -I - "$OUT/report.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
stages = r["stages"]
if len(stages) != 6: print("FAIL: expected 6 stages, got", len(stages)); sys.exit(1)
for s in stages:
    for k in ("bridge_delivery_fact_ids", "ranked_cue_fact_ids", "events_lacking_facts_and_has_delivery"):
        if k not in s: print("FAIL: stage", s.get("stage"), "lacks", k); sys.exit(1)
print("OK: bridge events in 3C:", r["3c_bridge_event_ids"], "| 3C deliveries:", r["3c_delivery_fact_ids"])
print("cue source per stage:", [(s["stage"], s["bridge_delivery_fact_ids"]) for s in stages])
PY
