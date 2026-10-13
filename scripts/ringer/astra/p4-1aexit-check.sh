#!/bin/bash
# Ringer check (outside the worker sandbox): live bench of scene 1A, 8 turns, counting whether and when 1A is left.
# Usage: p4-1aexit-check.sh OUT_DIR TREE VARIATION_FILE REPLICATES
set -u
OUT=$1; TREE=$2; VAR=$3; REPS=$4
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
set -a; source /home/bcorfman/dev/freytag-forge/.env; set +a
mkdir -p "$OUT"; rm -rf "$OUT/run"
cd "$TREE" || exit 1
PYTHONPATH="$TREE" TMPDIR=/tmp "$PY" -m bench run --variation "$VAR" --scene 1A --script s1 --replicates "$REPS" --out "$OUT/run" --confirm > "$OUT/bench.log" 2>&1 || { echo "FAIL bench"; tail -20 "$OUT/bench.log"; exit 1; }
"$PY" - "$OUT/run/all-turn-records.json" <<'PYEOF'
import json, sys
runs = json.load(open(sys.argv[1]))["runs"]
exits = []
for r in runs:
    turns = r.get("turns", [])
    first = next((t["turn_number"] for t in turns if t.get("left_scene")), None)
    exits.append(first)
    print(f"replicate {r.get('replicate')} status={r.get('status')} turns={len(turns)} rejected={r.get('rejected_turn_count')} left_1A_at_turn={first}")
print(f"SUMMARY runs={len(runs)} exited_within_4={sum(1 for e in exits if e is not None and e<=4)} exited_within_8={sum(1 for e in exits if e is not None)}")
PYEOF
