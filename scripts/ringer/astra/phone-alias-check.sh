#!/bin/bash
# Ringer check (runs outside the worker sandbox): live bench of "Examine Michelle's phone." in 1A, both arms.
# Usage: phone-alias-check.sh OUT_DIR REPLICATES
set -u
OUT=$1
REPS=$2
REPO=/home/bcorfman/dev/freytag-forge
PY=$REPO/.venv/bin/python
cd "$REPO" || exit 1
mkdir -p "$OUT"
for arm in baseline current; do
  rm -rf "$OUT/$arm"
  "$PY" -m bench run --variation bench/variations/astra-phone-$arm.json --scene 1A --script phone \
    --replicates "$REPS" --out "$OUT/$arm" --confirm > "$OUT/$arm.log" 2>&1 || { echo "FAIL bench $arm"; tail -20 "$OUT/$arm.log"; exit 1; }
done
"$PY" - "$OUT" "$REPS" <<'PYEOF'
import json, re, sys
from pathlib import Path
out, reps = Path(sys.argv[1]), int(sys.argv[2])
words = re.compile(r"\b(photo|photograph|picture)s?\b", re.I)
rows = {}
for arm in ("baseline", "current"):
    f = out / arm / "all-turn-records.json"
    if not f.exists():
        print("FAIL no records for", arm); sys.exit(1)
    runs = json.loads(f.read_text())["runs"]
    row = {"runs": len(runs), "narrated": 0, "rejected": 0, "photo_rejections": 0,
           "recovery_requests": 0, "photo_word_narrations": 0, "reasons": []}
    for run in runs:
        row["recovery_requests"] += run.get("recovery_requests", 0)
        row["narrated"] += run.get("narration_turns", 0)
        for t in run.get("turns", []):
            if words.search(t.get("narration") or ""):
                row["photo_word_narrations"] += 1
        for r in run.get("rejected_turns", []):
            row["rejected"] += 1
            text = json.dumps(r)
            row["reasons"].append(text[:200])
            if re.search(r"photo", text, re.I):
                row["photo_rejections"] += 1
    rows[arm] = row
    print(arm, json.dumps(row))
    if row["runs"] != reps:
        print("FAIL expected", reps, "runs"); sys.exit(1)
(out / "summary.json").write_text(json.dumps(rows, indent=1))
PYEOF
