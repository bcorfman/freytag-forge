#!/usr/bin/env bash
# T9h hidden bench matcher probe. Each stage is billed once; never rerun after a partial result.
set -u
STAGE="${1:-}"
if [ "$STAGE" != "probe" ]; then
  echo "usage: enforce_t9h_hidden_probe.sh probe" >&2
  exit 2
fi

ROOT=/home/bcorfman/dev/freytag-forge
PORT=8801
OUT="$ROOT/bench/results/environment-narration/t9h-hidden/probe"
ROWS="$OUT/rows.json"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp

if [ -e "$ROWS" ]; then
  echo "rows already exist at $ROWS; this billed stage will not run again" >&2
  exit 4
fi
if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
  echo "port $PORT is already in use; nothing was run" >&2
  exit 4
fi
mkdir -p "$OUT"

WORKER_PID=""
cleanup() {
  status=$?
  if [ -n "$WORKER_PID" ]; then
    curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/__spent.json" 2> /dev/null || true
    kill "$WORKER_PID" 2> /dev/null || true
    wait "$WORKER_PID" 2> /dev/null || true
  fi
  exit "$status"
}
trap cleanup EXIT

node scripts/ringer/environment_narration/local_worker.mjs --port "$PORT" --max-usd 0.02 > "$OUT/worker.log" 2>&1 &
WORKER_PID=$!
for _ in $(seq 1 50); do
  curl -fs "http://127.0.0.1:$PORT/__spent" > /dev/null 2>&1 && break
  sleep 0.2
done
if ! curl -fs "http://127.0.0.1:$PORT/__spent" > /dev/null 2>&1; then
  echo "local worker did not start" >&2
  exit 3
fi

export CLOUDFLARE_WORKER_URL="http://127.0.0.1:$PORT"
"$ROOT/.venv/bin/python" scripts/ringer/environment_narration/hidden_bench_matcher_probe.py \
  --run --confirm --max-calls 120 --max-usd 0.02 --out "$ROWS"
