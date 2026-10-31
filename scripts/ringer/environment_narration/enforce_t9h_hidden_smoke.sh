#!/usr/bin/env bash
# T9h hidden bench-clues Route E smoke. This stage is billed once; never rerun.
set -u

ROOT=/home/bcorfman/dev/freytag-forge
PORT=8803
OUT="$ROOT/bench/results/environment-narration/t9h-hidden/smoke"
ROWS="$OUT/rows"
WORKER_PID=""

cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp

if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
  echo "port $PORT is already in use; nothing was run" >&2
  exit 4
fi

if [ -d "$ROWS" ] && [ -n "$(find "$ROWS" -mindepth 1 -maxdepth 1 -type f -print -quit)" ]; then
  echo "$ROWS already holds rows; nothing was run" >&2
  exit 4
fi

mkdir -p "$OUT"
node "$ROOT/scripts/ringer/environment_narration/local_worker.mjs" --port "$PORT" --max-usd 0.07 > "$OUT/worker.log" 2>&1 &
WORKER_PID=$!

cleanup() {
  curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent.json" 2> /dev/null || true
  if [ -n "$WORKER_PID" ]; then
    kill "$WORKER_PID" 2> /dev/null || true
    wait "$WORKER_PID" 2> /dev/null || true
  fi
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
/home/bcorfman/dev/freytag-forge/.venv/bin/python scripts/ringer/transcript_1a/live_baseline.py \
  --route observe_park_bench_1b --enforce --replicates 3 --max-calls 240 --confirm --out "$ROWS"
