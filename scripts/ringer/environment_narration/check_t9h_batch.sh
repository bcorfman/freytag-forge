#!/usr/bin/env bash
# Check for the Jev batching and concurrency task. Free: no network, no model call.
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
SCRATCH=/tmp/t9h-batch
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
test -f tests/test_jev_batching.py || { echo "FAIL: tests/test_jev_batching.py missing" >&2; exit 1; }
"$PY" -m pytest -q -p no:cacheprovider --no-cov tests/test_jev_batching.py tests/test_hedged_request.py tests/test_cloudflare_transport.py tests/test_jev_questions.py tests/test_jev_use.py tests/test_runtime_jev.py tests/test_jev_summary.py tests/test_item_facts_null_place.py tests/test_bench_item_facts.py tests/test_live_baseline_evidence.py tests/test_hidden_clues_smoke_report.py tests/test_hidden_bench_discovery.py > "$SCRATCH/pytest.out" 2>&1
rc=$?; tail -25 "$SCRATCH/pytest.out"; [ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
CHANGED=$(git diff --name-only -- storygame tests | grep -E '\.py$' | tr '\n' ' ')
# shellcheck disable=SC2086
"$PY" -m ruff check $CHANGED tests/test_jev_batching.py || exit 1
# shellcheck disable=SC2086
"$PY" -m ruff format --check $CHANGED tests/test_jev_batching.py || exit 1
# Batching must cut the stubbed Jev call count on the unchanged Route E, with behaviour unchanged (S1 to S6 PASS).
FREYTAG_JEV_BATCH=0 "$PY" scripts/ringer/transcript_1a/live_baseline.py --route observe_park_bench_1b --enforce --replicates 3 --max-calls 240 --dry-run --out "$SCRATCH/off" > /dev/null || { echo "FAIL: dry-run with batching off" >&2; exit 1; }
"$PY" scripts/ringer/transcript_1a/live_baseline.py --route observe_park_bench_1b --enforce --replicates 3 --max-calls 240 --dry-run --out "$SCRATCH/on" > /dev/null || { echo "FAIL: dry-run with batching on" >&2; exit 1; }
"$PY" - "$SCRATCH" <<'PY' || exit 1
import json
import sys

base = sys.argv[1]
def calls(path):
    return json.load(open(f"{path}/summary.json", encoding="utf-8"))["calls_made"]
off, on = calls(base + "/off"), calls(base + "/on")
print(f"stubbed HTTP calls on 3x6 turns: batching off {off}, on {on}")
assert on < off, "batching did not reduce the stubbed call count"
PY
"$PY" scripts/ringer/environment_narration/hidden_clues_smoke_report.py "$SCRATCH/on" > "$SCRATCH/report.txt" || { cat "$SCRATCH/report.txt"; echo "FAIL: smoke report on batched dry rows" >&2; exit 1; }
for g in S1 S2 S3 S4 S5 S6; do grep -q "^$g: PASS" "$SCRATCH/report.txt" || { echo "FAIL: $g not PASS with batching on" >&2; exit 1; }; done
echo "batch checks ok"
