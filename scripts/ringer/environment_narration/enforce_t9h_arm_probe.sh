#!/usr/bin/env bash
# T9h stage 2 diagnostic arm screen. This stage is billed once; never rerun partial rows.
set -u

ROOT=/home/bcorfman/dev/freytag-forge
PORT=8803
OUT="$ROOT/bench/results/environment-narration/t9h-stage2-diagnostic"
ROWS="$OUT/rows.json"
CAPTURE="$OUT/capture.json"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp

if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
  echo "port $PORT is already in use; nothing was run" >&2
  exit 4
fi
if [ -e "$ROWS" ]; then
  echo "rows already exist at $ROWS; nothing was run" >&2
  exit 4
fi

mkdir -p "$OUT"
.venv/bin/python scripts/ringer/environment_narration/hidden_bench_arm_probe.py --validate || exit $?
.venv/bin/python scripts/ringer/environment_narration/hidden_bench_arm_probe.py --capture --out "$CAPTURE" || exit $?

node scripts/ringer/environment_narration/local_worker.mjs --port "$PORT" --max-usd 0.03 > "$OUT/worker.log" 2>&1 &
WORKER_PID=$!
cleanup() {
  kill "$WORKER_PID" 2> /dev/null || true
  wait "$WORKER_PID" 2> /dev/null || true
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
.venv/bin/python scripts/ringer/environment_narration/hidden_bench_arm_probe.py \
  --run --confirm --max-calls 30 --max-usd 0.03 --out "$ROWS"
