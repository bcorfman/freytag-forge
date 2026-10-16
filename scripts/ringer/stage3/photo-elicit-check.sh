#!/bin/bash
# Ringer check (runs outside the worker sandbox, BILLED local narration bench).
# Usage: photo-elicit-check.sh OUT_DIR REPLICATES   -- 3 photo-eliciting 1A prompts x 2 alias arms.
set -u
OUT=$1; REPS=$2
REPO=/home/bcorfman/dev/freytag-forge; PY=$REPO/.venv/bin/python
cd "$REPO" || exit 1
mkdir -p "$OUT"
for arm in baseline current; do
  for script in photos picture photograph; do
    rm -rf "$OUT/$arm-$script"
    "$PY" -m bench run --variation bench/variations/stage3-photo-$arm.json --scene 1A --script $script \
      --replicates "$REPS" --out "$OUT/$arm-$script" --confirm > "$OUT/$arm-$script.log" 2>&1 \
      || { echo "FAIL bench $arm $script"; tail -20 "$OUT/$arm-$script.log"; exit 1; }
  done
done
"$PY" scripts/ringer/stage3/photo_elicit_report.py "$OUT" "$REPS"
