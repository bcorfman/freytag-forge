#!/usr/bin/env bash
# T9 stage-1 enforcing-verifier run against a local Worker (see
# .plans/grounded-llm-environment-narration/t9-enforce-stage1-prereg.md).
# Usage: enforce_stage1.sh smoke|full. Each stage is billed once; never rerun after a partial result.
set -u
STAGE="${1:-}"
case "$STAGE" in
  smoke) ARGS="--replicates 1 --max-calls 70"; MAX_USD=0.03 ;;
  full) ARGS="--replicates 10 --max-calls 700"; MAX_USD=0.20 ;;
  *) echo "usage: enforce_stage1.sh smoke|full" >&2; exit 2 ;;
esac
ROOT=/home/bcorfman/dev/freytag-forge
PORT=8795
OUT="$ROOT/bench/results/environment-narration/enforce-stage1/$STAGE"
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
.venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_topup --enforce $ARGS --confirm --out "$OUT/rows"
echo "$STAGE exit: $?"
curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent.json"
kill "$WORKER_PID" 2> /dev/null
wait "$WORKER_PID" 2> /dev/null
cat "$OUT/spent.json"
