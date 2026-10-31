#!/usr/bin/env bash
# T9h opening-condition judge. This stage is billed and runs once.
set -u

STAGE="${1:-}"
VERSION="${2:-v3}"
ROOT=/home/bcorfman/dev/freytag-forge
ED=scripts/ringer/environment_narration
CASE_ARGS=()
case "$VERSION" in
  v3)
    OUT="$ROOT/bench/results/environment-narration/t9h-opening-v3"
    PORT=8817
    ;;
  v4)
    OUT="$ROOT/bench/results/environment-narration/t9h-opening-v4"
    PORT=8819
    CASE_ARGS=(
      --cases "$ROOT/scripts/ringer/environment_narration/drain_condition_judge/cases-v4.jsonl"
      --lock "$ROOT/scripts/ringer/environment_narration/drain_condition_judge/lock-v4.json"
      --relabelled "$ROOT/scripts/ringer/environment_narration/drain_condition_judge/relabelled-v4.json"
    )
    ;;
  *)
    echo "usage: enforce_t9h_opening_v3.sh judge [v3|v4]" >&2
    exit 2
    ;;
esac
ROWS="$OUT/judge/rows.json"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp

if [ "$STAGE" != judge ]; then
  echo "usage: enforce_t9h_opening_v3.sh judge [v3|v4]" >&2
  exit 2
fi
if [ -e "$ROWS" ]; then
  echo "rows already exist at $ROWS; nothing was run" >&2
  exit 4
fi
if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2> /dev/null; then
  exec 3>&-
  echo "port $PORT is already in use; nothing was run" >&2
  exit 4
fi

mkdir -p "$OUT/judge"
node "$ED/local_worker.mjs" --port "$PORT" --max-usd 0.05 > "$OUT/judge/worker.log" 2>&1 &
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
"$ROOT/.venv/bin/python" "$ED/opening_condition_v3.py" \
  --judge --confirm --max-calls 900 --max-usd 0.05 --min-interval-s 0.5 --out "$ROWS" "${CASE_ARGS[@]}" || exit $?

set +e
"$ROOT/.venv/bin/python" "$ED/opening_condition_v3.py" \
  --report --rows "$ROWS" --out "$OUT/report.md" "${CASE_ARGS[@]}"
REPORT_RC=$?
set -u
printf '%s\n' "$REPORT_RC" > "$OUT/report.exit"
curl -fs "http://127.0.0.1:$PORT/__spent" > "$OUT/spent.json"
exit 0
