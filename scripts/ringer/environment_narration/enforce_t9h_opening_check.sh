#!/usr/bin/env bash
# T9h opening-condition check smoke run with the enforcing verifier enabled.
# Usage: enforce_t9h_opening_check.sh smoke. This run is billed; never rerun after a partial result.
set -u
STAGE="${1:-}"
case "$STAGE" in
  smoke)
    ARGS="--replicates 3 --max-calls 40"
    ;;
  retry)
    ARGS="--opening-retry-fact --replicates 5 --max-calls 60"
    ;;
  things)
    ARGS="--opening-things-fact --replicates 5 --max-calls 60"
    ;;
  *) echo "usage: enforce_t9h_opening_check.sh smoke|retry|things" >&2; exit 2 ;;
esac

ROOT=/home/bcorfman/dev/freytag-forge
PORT=8813
OUT="$ROOT/bench/results/environment-narration/t9h-opening-check/$STAGE"
ROUTES="observe_storm_drain_1b observe_service_gate_1b observe_back_door_1a"
if [ "$STAGE" = "retry" ]; then
  PORT=8814
elif [ "$STAGE" = "things" ]; then
  PORT=8815
fi
cd "$ROOT" || exit 2
mkdir -p "$OUT"
export PYTHONPATH="$ROOT" TMPDIR=/tmp

for route in $ROUTES; do
  if [ -e "$OUT/$route/rows" ]; then
    echo "rows directory already exists for $route; nothing was run" >&2
    exit 4
  fi
done

if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
  echo "port $PORT is already in use; nothing was run" >&2
  exit 4
fi

node scripts/ringer/environment_narration/local_worker.mjs --port "$PORT" --max-usd 0.06 > "$OUT/worker.log" 2>&1 &
WORKER_PID=$!
cleanup() {
  kill "$WORKER_PID" 2> /dev/null
  wait "$WORKER_PID" 2> /dev/null
}
trap cleanup EXIT

for _ in $(seq 1 50); do
  curl -fs "http://127.0.0.1:$PORT/__spent" > /dev/null 2>&1 && break
  sleep 0.2
done
if ! curl -fs "http://127.0.0.1:$PORT/__spent" > /dev/null 2>&1; then
  echo "local worker did not start" >&2
  exit 3
fi

export CLOUDFLARE_WORKER_URL="http://127.0.0.1:$PORT"
for route in $ROUTES; do
  # shellcheck disable=SC2086
  .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route "$route" --enforce --scene-state --opening-check $ARGS --confirm --out "$OUT/$route/rows"
  route_exit=$?
  echo "$route exit: $route_exit"
  if [ "$route_exit" -ne 0 ]; then
    exit "$route_exit"
  fi
  stopped_reason="$(.venv/bin/python - "$OUT/$route/rows/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1]))
print("null" if summary.get("stopped_reason") is None else summary["stopped_reason"])
PY
  )"
  if [ "$stopped_reason" != "null" ]; then
    echo "$route stopped with $stopped_reason; sequence halted" >&2
    exit 1
  fi
done

curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent.json"
