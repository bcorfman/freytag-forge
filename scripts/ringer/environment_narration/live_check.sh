#!/usr/bin/env bash
# Billed live check of the whole product path against a local Worker with a hard dollar cap.
# Each billed command runs once; the caller must never rerun this script after a partial result.
set -u
ROOT=/home/bcorfman/dev/freytag-forge
OUT="$ROOT/bench/results/environment-narration/live-check"
PORT=8791
MAX_USD=0.25
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
.venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route reported --replicates 2 --max-calls 60 --confirm --out "$OUT/reported"
echo "reported exit: $?"
curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent-after-reported.json"
.venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route corrected --replicates 2 --max-calls 85 --confirm --out "$OUT/corrected"
echo "corrected exit: $?"
curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent.json"
kill "$WORKER_PID" 2> /dev/null
wait "$WORKER_PID" 2> /dev/null
cat "$OUT/spent.json"
