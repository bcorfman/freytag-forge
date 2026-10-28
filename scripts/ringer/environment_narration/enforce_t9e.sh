#!/usr/bin/env bash
# T9e search-opens and repeatable-handoff enforced run.
# Usage: enforce_t9e.sh smoke|full. Each stage is billed once; never rerun after a partial result.
set -u
STAGE="${1:-}"
case "$STAGE" in
  smoke)
    ARGS_A="--replicates 1 --max-calls 90"
    ARGS_B="--replicates 1 --max-calls 40"
    ARGS_C="--replicates 2 --max-calls 90"
    MAX_USD=0.07
    ;;
  full)
    ARGS_A="--replicates 10 --max-calls 800"
    ARGS_B="--replicates 5 --max-calls 250"
    ARGS_C="--replicates 15 --max-calls 700"
    MAX_USD=0.45
    ;;
  *) echo "usage: enforce_t9e.sh smoke|full" >&2; exit 2 ;;
esac
ROOT=/home/bcorfman/dev/freytag-forge
PORT=8797
OUT="$ROOT/bench/results/environment-narration/t9e-check/$STAGE"
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
.venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_topup --enforce $ARGS_A --confirm --out "$OUT/a/rows"
A_EXIT=$?
echo "A exit: $A_EXIT"

if [ -f "$OUT/a/rows/summary.json" ]; then
  A_STOP_REASON="$([ -x .venv/bin/python ] && .venv/bin/python - "$OUT/a/rows/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
print("null" if summary.get("stopped_reason") is None else summary["stopped_reason"])
PY
  )"
else
  A_STOP_REASON="missing summary.json"
fi

if [ "$A_STOP_REASON" = "null" ]; then
  # shellcheck disable=SC2086
  .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_under_first --enforce $ARGS_B --confirm --out "$OUT/b/rows"
  B_EXIT=$?
  echo "B exit: $B_EXIT"
else
  echo "B skipped: A stopped with $A_STOP_REASON"
fi

if [ "$A_STOP_REASON" = "null" ] && [ -f "$OUT/b/rows/summary.json" ]; then
  B_STOP_REASON="$([ -x .venv/bin/python ] && .venv/bin/python - "$OUT/b/rows/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
print("null" if summary.get("stopped_reason") is None else summary["stopped_reason"])
PY
  )"
else
  B_STOP_REASON="missing summary.json"
fi

if [ "$A_STOP_REASON" = "null" ] && [ "$B_STOP_REASON" = "null" ]; then
  # shellcheck disable=SC2086
  .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_look_inside_under --enforce $ARGS_C --confirm --out "$OUT/c/rows"
  C_EXIT=$?
  echo "C exit: $C_EXIT"
else
  echo "C skipped: B stopped with $B_STOP_REASON"
fi

curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent.json"
echo "spent.json:"
cat "$OUT/spent.json"
kill "$WORKER_PID" 2> /dev/null
wait "$WORKER_PID" 2> /dev/null
