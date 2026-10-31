#!/usr/bin/env bash
# T9h J1c drain run with the enforcing verifier off and on.
# Usage: enforce_t9h_drain.sh smoke|full. Each stage is billed once; never rerun after a partial result.
set -u
STAGE="${1:-}"
case "$STAGE" in
  smoke)
    ARGS="--replicates 3 --max-calls 40"
    MAX_USD=0.04
    ;;
  full)
    ARGS="--replicates 20 --max-calls 220"
    MAX_USD=0.20
    ;;
  *) echo "usage: enforce_t9h_drain.sh smoke|full" >&2; exit 2 ;;
esac
ROOT=/home/bcorfman/dev/freytag-forge
PORT=8797
OUT="$ROOT/bench/results/environment-narration/t9h-drain/$STAGE"
cd "$ROOT" || exit 2
mkdir -p "$OUT"
export PYTHONPATH="$ROOT" TMPDIR=/tmp
set -a; . ./.env; set +a
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
