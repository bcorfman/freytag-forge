#!/usr/bin/env bash
# T9h opening-condition v2. Each billed stage is run at most once.
set -u

STAGE="${1:-}"
ROOT=/home/bcorfman/dev/freytag-forge
ED=scripts/ringer/environment_narration
OUT="$ROOT/bench/results/environment-narration/t9h-opening-v2"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp

case "$STAGE" in
  generate)
    PORT=8811
    ROWS="$OUT/generate-2/rows.json"
    mkdir -p "$OUT/generate-2"
    if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
      exec 3>&-
      echo "port $PORT is already in use; nothing was run" >&2
      exit 4
    fi
    if [ -e "$ROWS" ]; then
      echo "rows already exist at $ROWS; nothing was run" >&2
      exit 4
    fi
    if [ ! -e "$OUT/capture.json" ]; then
      "$ROOT/.venv/bin/python" "$ED/opening_condition_v2.py" --capture --out "$OUT/capture.json" || exit $?
    fi
    node scripts/ringer/environment_narration/local_worker.mjs --port 8811 --max-usd 0.057 > "$OUT/generate-2/worker.log" 2>&1 &
    WORKER_PID=$!
    cleanup() {
      kill "$WORKER_PID" 2> /dev/null || true
      wait "$WORKER_PID" 2> /dev/null || true
    }
    trap cleanup EXIT
    for _ in $(seq 1 50); do
      curl -fs "http://127.0.0.1:8811/__spent" > /dev/null 2>&1 && break
      sleep 0.2
    done
    if ! curl -fs "http://127.0.0.1:8811/__spent" > /dev/null 2>&1; then
      echo "local worker did not start" >&2
      exit 3
    fi
    export CLOUDFLARE_WORKER_URL="http://127.0.0.1:8811"
    "$ROOT/.venv/bin/python" "$ED/opening_condition_v2.py" \
      --run --capture "$OUT/capture.json" --confirm --samples 10 --max-calls 44 --max-usd 0.057 --out "$ROWS"
    ;;
  judge)
    PORT=8812
    ROWS="$OUT/judge/rows.json"
    if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
      exec 3>&-
      echo "port $PORT is already in use; nothing was run" >&2
      exit 4
    fi
    if [ -e "$ROWS" ]; then
      echo "rows already exist at $ROWS; nothing was run" >&2
      exit 4
    fi
    mkdir -p "$OUT/judge"
    node scripts/ringer/environment_narration/local_worker.mjs --port 8812 --max-usd 0.02 > "$OUT/judge/worker.log" 2>&1 &
    WORKER_PID=$!
    cleanup() {
      kill "$WORKER_PID" 2> /dev/null || true
      wait "$WORKER_PID" 2> /dev/null || true
    }
    trap cleanup EXIT
    for _ in $(seq 1 50); do
      curl -fs "http://127.0.0.1:8812/__spent" > /dev/null 2>&1 && break
      sleep 0.2
    done
    if ! curl -fs "http://127.0.0.1:8812/__spent" > /dev/null 2>&1; then
      echo "local worker did not start" >&2
      exit 3
    fi
    export CLOUDFLARE_WORKER_URL="http://127.0.0.1:8812"
    "$ROOT/.venv/bin/python" "$ED/opening_condition_v2.py" \
      --judge --confirm --samples 5 --max-calls 200 --max-usd 0.02 --min-interval-s 0.5 --cases "$OUT/cases" --out "$ROWS" || exit $?
    "$ROOT/.venv/bin/python" "$ED/opening_condition_v2.py" \
      --report --cases "$OUT/cases" --rows "$ROWS" --out "$OUT/report.md"
    ;;
  *)
    echo "usage: enforce_t9h_opening_v2.sh generate|judge" >&2
    exit 2
    ;;
esac
