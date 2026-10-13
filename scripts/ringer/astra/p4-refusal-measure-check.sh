#!/bin/bash
# Ringer check (runs outside the worker sandbox): live bench of the four refusal arms on fixed-thing commands in 1A.
# Usage: p4-refusal-measure-check.sh OUT_DIR REPLICATES "ARMS" ["SCRIPTS"]
set -u
OUT=$1; REPS=$2; ARMS=${3:-"off clause repair renarrate"}; SCRIPTS=${4:-"s1 s2 s3 s4"}
REPO=/home/bcorfman/dev/freytag-forge
PY=$REPO/.venv/bin/python
cd "$REPO" || exit 1
mkdir -p "$OUT"
for arm in $ARMS; do
  for s in $SCRIPTS; do
    rm -rf "$OUT/$arm/$s"
    "$PY" -m bench run --variation bench/variations/astra-p4-refusal-$arm.json --scene 1A --script "$s" \
      --replicates "$REPS" --out "$OUT/$arm/$s" --confirm > "$OUT/$arm-$s.log" 2>&1 || { echo "FAIL bench $arm $s"; tail -20 "$OUT/$arm-$s.log"; exit 1; }
  done
done
"$PY" - "$OUT" "$ARMS" "$SCRIPTS" <<'PYEOF'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
for arm in sys.argv[2].split():
    tot = ref = extra = fallback = 0
    miss = judged = 0
    for s in sys.argv[3].split():
        f = out / arm / s / "all-turn-records.json"
        if not f.exists():
            print("FAIL no records", arm, s); sys.exit(1)
        for run in json.loads(f.read_text())["runs"]:
            for t in run.get("turns", []):
                tot += 1
                cap = [i for i in (t.get("capture_issues") or []) + (t.get("item_facts_issues") or [])]
                r = [i for i in cap if "refused place" in i]
                ref += bool(r)
                extra += t.get("refusal_extra_calls", 0) or 0
                fallback += any("re-narration failed" in i for i in cap)
                print(f"== {arm} {s} refused={bool(r)} extra_calls={t.get('refusal_extra_calls')}\n  notes: {[i for i in cap if 'refusal' in i]}\n  narr: {(t.get('narration') or '').replace(chr(10),' ')}")
        sm = out / arm / s / "summary.json"
        if sm.exists():
            ft = (json.loads(sm.read_text()).get("fact_tracking") or {})
            print(f"  judge[{arm} {s}]: {json.dumps(ft)[:400]}")
    print(f"SUMMARY arm={arm} turns={tot} refused={ref} extra_calls={extra} fallbacks={fallback}")
PYEOF
