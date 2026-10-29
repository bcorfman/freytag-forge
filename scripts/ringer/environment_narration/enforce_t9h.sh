#!/usr/bin/env bash
# T9h enforced observation run on new supporters and scenes.
# Usage: enforce_t9h.sh smoke|full. Each stage is billed once; never rerun after a partial result.
set -u
STAGE="${1:-}"
case "$STAGE" in
  smoke)
    ARGS_C="--replicates 1 --max-calls 50"
    ARGS_D="--replicates 2 --max-calls 90"
    ARGS_E="--replicates 2 --max-calls 90"
    ARGS_F="--replicates 2 --max-calls 90"
    MAX_USD=0.07
    ;;
  full)
    ARGS_C="--replicates 5 --max-calls 250"
    ARGS_D="--replicates 10 --max-calls 450"
    ARGS_E="--replicates 10 --max-calls 450"
    ARGS_F="--replicates 10 --max-calls 450"
    MAX_USD=0.45
    ;;
  *) echo "usage: enforce_t9h.sh smoke|full" >&2; exit 2 ;;
esac
ROOT=/home/bcorfman/dev/freytag-forge
PORT=8798
OUT="$ROOT/bench/results/environment-narration/t9h/$STAGE"
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
.venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_look_inside_under --enforce $ARGS_C --confirm --out "$OUT/c/rows"
C_EXIT=$?
echo "C exit: $C_EXIT"

if [ -f "$OUT/c/rows/summary.json" ]; then
  C_STOP_REASON="$([ -x .venv/bin/python ] && .venv/bin/python - "$OUT/c/rows/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
print("null" if summary.get("stopped_reason") is None else summary["stopped_reason"])
PY
  )"
else
  C_STOP_REASON="missing summary.json"
fi

if [ "$C_STOP_REASON" = "null" ]; then
  # shellcheck disable=SC2086
  .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_supporters_1a --enforce $ARGS_D --confirm --out "$OUT/d/rows"
  D_EXIT=$?
  echo "D exit: $D_EXIT"
else
  echo "D skipped: C stopped with $C_STOP_REASON"
fi

if [ "$C_STOP_REASON" = "null" ] && [ -f "$OUT/d/rows/summary.json" ]; then
  D_STOP_REASON="$([ -x .venv/bin/python ] && .venv/bin/python - "$OUT/d/rows/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
print("null" if summary.get("stopped_reason") is None else summary["stopped_reason"])
PY
  )"
else
  D_STOP_REASON="missing summary.json"
fi

if [ "$C_STOP_REASON" = "null" ] && [ "$D_STOP_REASON" = "null" ]; then
  # shellcheck disable=SC2086
  .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_park_bench_1b --enforce $ARGS_E --confirm --out "$OUT/e/rows"
  E_EXIT=$?
  echo "E exit: $E_EXIT"
else
  echo "E skipped: D stopped with $D_STOP_REASON"
fi

if [ "$C_STOP_REASON" = "null" ] && [ "$D_STOP_REASON" = "null" ] && [ -f "$OUT/e/rows/summary.json" ]; then
  E_STOP_REASON="$([ -x .venv/bin/python ] && .venv/bin/python - "$OUT/e/rows/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
print("null" if summary.get("stopped_reason") is None else summary["stopped_reason"])
PY
  )"
else
  E_STOP_REASON="missing summary.json"
fi

if [ "$C_STOP_REASON" = "null" ] && [ "$D_STOP_REASON" = "null" ] && [ "$E_STOP_REASON" = "null" ]; then
  # shellcheck disable=SC2086
  .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_executive_desk_3b --enforce $ARGS_F --confirm --out "$OUT/f/rows"
  F_EXIT=$?
  echo "F exit: $F_EXIT"
else
  echo "F skipped: E stopped with $E_STOP_REASON"
fi

curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent.json"
echo "spent.json:"
cat "$OUT/spent.json"
kill "$WORKER_PID" 2> /dev/null
wait "$WORKER_PID" 2> /dev/null
