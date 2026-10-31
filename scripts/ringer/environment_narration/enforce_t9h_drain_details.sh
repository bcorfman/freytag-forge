#!/usr/bin/env bash
# T9h drain-details prose screen. This stage is billed once; never rerun partial rows.
set -u

STAGE="${1:-}"
case "$STAGE" in
  screen)
    PORT=8804
    SAMPLES=10
    MAX_CALLS=20
    MAX_USD=0.03
    ;;
  confirm)
    PORT=8805
    SAMPLES=15
    MAX_CALLS=30
    MAX_USD=0.06
    ;;
  *)
    echo "usage: enforce_t9h_drain_details.sh screen|confirm" >&2
    exit 2
    ;;
esac

ROOT=/home/bcorfman/dev/freytag-forge
OUT="$ROOT/bench/results/environment-narration/t9h-drain-details/$STAGE"
ROWS="$OUT/rows.json"
CAPTURE="$OUT/capture.json"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp

if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
  exec 3>&-
  echo "port $PORT is already in use; nothing was run" >&2
  exit 4
fi
if [ -e "$ROWS" ]; then
  echo "rows already exist at $ROWS; nothing was run" >&2
  exit 4
fi

mkdir -p "$OUT"
.venv/bin/python scripts/ringer/environment_narration/drain_details_prose_probe.py \
  --capture --samples "$SAMPLES" --out "$CAPTURE" || exit $?

node scripts/ringer/environment_narration/local_worker.mjs --port "$PORT" --max-usd "$MAX_USD" > "$OUT/worker.log" 2>&1 &
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
.venv/bin/python scripts/ringer/environment_narration/drain_details_prose_probe.py \
  --run --confirm --samples "$SAMPLES" --max-calls "$MAX_CALLS" --max-usd "$MAX_USD" --out "$ROWS"
