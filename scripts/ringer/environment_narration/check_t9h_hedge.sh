#!/usr/bin/env bash
# Check for the hedged-request task. Free: no network, no model call.
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
SCRATCH=/tmp/t9h-hedge
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
test -f storygame/runtime/hedged_request.py && test -f tests/test_hedged_request.py || { echo "FAIL: hedged_request module or its tests missing" >&2; exit 1; }
FILES="storygame/runtime/hedged_request.py storygame/runtime/cloudflare.py storygame/runtime/jev.py tests/test_hedged_request.py"
"$PY" -m pytest -q -p no:cacheprovider --no-cov tests/test_hedged_request.py tests/test_cloudflare_transport.py tests/test_jev_questions.py tests/test_jev_use.py tests/test_runtime_jev.py tests/test_jev_summary.py tests/test_item_facts_null_place.py tests/test_bench_item_facts.py tests/test_live_baseline_evidence.py tests/test_hidden_clues_smoke_report.py > "$SCRATCH/pytest.out" 2>&1
rc=$?; tail -25 "$SCRATCH/pytest.out"; [ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
# shellcheck disable=SC2086
"$PY" -m ruff check $FILES || exit 1
# shellcheck disable=SC2086
"$PY" -m ruff format --check $FILES || exit 1
# The unchanged Route E smoke still evaluates S1 to S6 end to end on stubbed calls.
"$PY" scripts/ringer/transcript_1a/live_baseline.py --route observe_park_bench_1b --enforce --replicates 3 --max-calls 240 --dry-run --out "$SCRATCH/dry" > /dev/null || { echo "FAIL: route E dry-run" >&2; exit 1; }
"$PY" scripts/ringer/environment_narration/hidden_clues_smoke_report.py "$SCRATCH/dry" > "$SCRATCH/report.txt" || { cat "$SCRATCH/report.txt"; echo "FAIL: smoke report on dry rows" >&2; exit 1; }
for g in S1 S2 S3 S4 S5 S6; do grep -q "^$g: PASS" "$SCRATCH/report.txt" || { echo "FAIL: $g not PASS on the dry run" >&2; exit 1; }; done
echo "hedge checks ok"
