#!/bin/bash
# Ringer check (outside sandbox): live bench of known guard-rejection prompts in 1A, then the guard-retry report (every turn printed).
# Usage: guard-retry-measure-check.sh OUT_DIR REPLICATES [SCRIPTS...]
set -u
OUT=$1; REPS=$2; shift 2
VAR=${VARIATION:-scripts/ringer/astra/guard-retry-measure-variation.json}
SCRIPTS=${*:-g1 g2 g3}
REPO=/home/bcorfman/dev/freytag-forge
PY=$REPO/.venv/bin/python
cd "$REPO" || exit 1
[ -z "$(git status --porcelain | grep -v -E 'scripts/ringer/astra/|\.plans/')" ] || [ "${ALLOW_DIRTY:-}" = 1 ] || { echo "FAIL dirty tree (set ALLOW_DIRTY=1 to override)"; exit 1; }
grep -q last_guard_rejections storygame/runtime/engine.py || { echo "FAIL telemetry not in this build"; exit 1; }
mkdir -p "$OUT"
echo "build $(git rev-parse HEAD) variation sha256 $(sha256sum "$VAR" | cut -c1-16)"
ARGS=()
for s in $SCRIPTS; do
  rm -rf "$OUT/$s"
  "$PY" -m bench run --variation "$VAR" --scene 1A --script "$s" \
    --replicates "$REPS" --out "$OUT/$s" --confirm > "$OUT/$s.log" 2>&1 || { echo "FAIL bench $s"; tail -20 "$OUT/$s.log"; exit 1; }
  [ -f "$OUT/$s/all-turn-records.json" ] || { echo "FAIL no records for $s"; exit 1; }
  ARGS+=(--in "$OUT/$s/all-turn-records.json")
done
"$PY" -m bench.guard_retry_report "${ARGS[@]}" --out-json "$OUT/report.json" --out-md "$OUT/report.md" || exit 1
cat "$OUT/report.md"
