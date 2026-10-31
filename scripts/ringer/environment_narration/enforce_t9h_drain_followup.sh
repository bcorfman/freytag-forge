#!/usr/bin/env bash
# T9h J1c drain follow-up smoke (hedges and batching off in both arms; fresh output directory).
# Usage: enforce_t9h_drain_followup.sh smoke. Each stage is billed once; never rerun after a partial result.
set -u
STAGE="${1:-}"
case "$STAGE" in
  smoke)
    ARGS="--replicates 3 --max-calls 40"
    MAX_USD=0.04
    ;;
  *) echo "usage: enforce_t9h_drain_followup.sh smoke" >&2; exit 2 ;;
esac
ROOT=/home/bcorfman/dev/freytag-forge
PORT=8806
OUT="$ROOT/bench/results/environment-narration/t9h-drain-followup/$STAGE"
cd "$ROOT" || exit 2
if [ -e "$OUT/off/rows" ] || [ -e "$OUT/on/rows" ]; then
  echo "rows already exist under $OUT; nothing was run" >&2
  exit 4
fi
mkdir -p "$OUT"
{
  echo "head: $(git rev-parse HEAD)"
  echo "settings: FREYTAG_JEV_BATCH=0 FREYTAG_HEDGE_DELAY_S=0 FREYTAG_HEDGE_NARRATION_S=0; args: $ARGS; max_usd: $MAX_USD"
  (cd data/stories/continuity-initiative && sha256sum * 2> /dev/null)
  sha256sum storygame/runtime/observation_verifier.py scripts/ringer/transcript_1a/live_baseline.py
} > "$OUT/settings.txt"
export PYTHONPATH="$ROOT" TMPDIR=/tmp
set -a; . ./.env; set +a
export FREYTAG_JEV_BATCH=0 FREYTAG_HEDGE_DELAY_S=0 FREYTAG_HEDGE_NARRATION_S=0
unset OPENAI_API_KEY RAILWAY_TOKEN RAILWAY_PROJECT_ID FREYTAG_TEST_CLOCK_TOKEN

if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
  echo "port $PORT is already in use; nothing was run" >&2
  exit 4
fi
node scripts/ringer/environment_narration/local_worker.mjs --port "$PORT" --max-usd "$MAX_USD" > "$OUT/worker.log" 2>&1 &
WORKER_PID=$!
for _ in $(seq 1 50); do
  curl -fs "http://127.0.0.1:$PORT/__spent" > /dev/null 2>&1 && break
  sleep 0.2
done
if ! curl -fs "http://127.0.0.1:$PORT/__spent" > /dev/null 2>&1; then
  echo "local worker did not start" >&2
  kill "$WORKER_PID" 2> /dev/null
  exit 3
fi

export CLOUDFLARE_WORKER_URL="http://127.0.0.1:$PORT"
# shellcheck disable=SC2086
.venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_storm_drain_1b --enforce $ARGS --confirm --out "$OUT/off/rows"
OFF_EXIT=$?
echo "OFF exit: $OFF_EXIT"

if [ -f "$OUT/off/rows/summary.json" ]; then
  OFF_STOP_REASON="$(.venv/bin/python - "$OUT/off/rows/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
print("null" if summary.get("stopped_reason") is None else summary["stopped_reason"])
PY
  )"
else
  OFF_STOP_REASON="missing summary.json"
fi

if [ "$OFF_STOP_REASON" = "null" ]; then
  # shellcheck disable=SC2086
  .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_storm_drain_1b --enforce --scene-state $ARGS --confirm --out "$OUT/on/rows"
  ON_EXIT=$?
  echo "ON exit: $ON_EXIT"
else
  echo "ON skipped: OFF stopped with $OFF_STOP_REASON"
fi

curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent.json"
echo "spent.json:"
cat "$OUT/spent.json"
kill "$WORKER_PID" 2> /dev/null
wait "$WORKER_PID" 2> /dev/null
