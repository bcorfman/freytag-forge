#!/bin/bash
# Ringer check (runs outside the worker sandbox): live bench of refusal-prone commands in 1A; prints per-turn refusal issues and narration.
# Usage: p4-refusal-probe-check.sh OUT_DIR REPLICATES [SCRIPTS...]
set -u
OUT=$1; REPS=$2; shift 2
SCRIPTS=${*:-r1 r2 r3 r4 r5 r6 r7 r8 r9}
REPO=/home/bcorfman/dev/freytag-forge
PY=$REPO/.venv/bin/python
cd "$REPO" || exit 1
mkdir -p "$OUT"
for s in $SCRIPTS; do
  rm -rf "$OUT/$s"
  "$PY" -m bench run --variation bench/variations/astra-p4-refusal-probe.json --scene 1A --script "$s" \
    --replicates "$REPS" --out "$OUT/$s" --confirm > "$OUT/$s.log" 2>&1 || { echo "FAIL bench $s"; tail -20 "$OUT/$s.log"; exit 1; }
done
"$PY" - "$OUT" $SCRIPTS <<'PYEOF'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
tot = ref = 0
for s in sys.argv[2:]:
    f = out / s / "all-turn-records.json"
    if not f.exists():
        print("FAIL no records for", s); sys.exit(1)
    for run in json.loads(f.read_text())["runs"]:
        for t in run.get("turns", []):
            tot += 1
            iss = [i for i in (t.get("item_facts_issues") or []) if "refused" in i]
            ref += bool(iss)
            print(f"== {s} refused={bool(iss)}\n  cmd: {t.get('player_input') or t.get('input')}\n  issues: {iss}\n  narr: {(t.get('narration') or '')[:500]}")
print(f"SUMMARY turns={tot} with_refusal={ref}")
PYEOF
