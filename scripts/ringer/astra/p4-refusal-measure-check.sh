#!/bin/bash
# Ringer check (runs outside the worker sandbox): live bench of the four refusal arms on fixed-thing commands in 1A.
# Optional environment: EXPECT_TURNS (turns per arm), EXPECT_REFUSED_MIN (minimum
# refusals per arm), and ALLOW_DIRTY=1 (allow changes under storygame/ or bench/).
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
SUMMARY_ARGS=()
if [[ -n "${EXPECT_TURNS:-}" ]]; then SUMMARY_ARGS+=(--expect-turns "$EXPECT_TURNS"); fi
if [[ -n "${EXPECT_REFUSED_MIN:-}" ]]; then SUMMARY_ARGS+=(--expect-refused-min "$EXPECT_REFUSED_MIN"); fi
"$PY" scripts/ringer/astra/refusal_summary.py "$OUT" "$ARMS" "$SCRIPTS" --repo "$REPO" "${SUMMARY_ARGS[@]}"
