#!/usr/bin/env bash
# Check for the narration hedge task. Free: no network, no model call.
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
SCRATCH=/tmp/t9h-narration-hedge
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
test -f tests/test_narration_hedge.py || { echo "FAIL: tests/test_narration_hedge.py missing" >&2; exit 1; }
"$PY" -m pytest -q -p no:cacheprovider --no-cov tests/test_narration_hedge.py tests/test_hedged_request.py tests/test_cloudflare_transport.py tests/test_jev_batching.py tests/test_jev_questions.py tests/test_runtime_jev.py tests/test_item_facts_null_place.py tests/test_bench_item_facts.py tests/test_live_baseline_evidence.py tests/test_hidden_clues_smoke_report.py tests/test_hidden_bench_discovery.py > "$SCRATCH/pytest.out" 2>&1
rc=$?; tail -25 "$SCRATCH/pytest.out"; [ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check storygame/runtime/cloudflare.py tests/test_narration_hedge.py tests/test_cloudflare_transport.py || exit 1
"$PY" -m ruff format --check storygame/runtime/cloudflare.py tests/test_narration_hedge.py tests/test_cloudflare_transport.py || exit 1
grep -q "ItemFactsProvider" tests/test_narration_hedge.py || { echo "FAIL: narration hedge tests must exercise the real ItemFactsProvider" >&2; exit 1; }
if grep -q "_request_without_hedge_retry" storygame/runtime/cloudflare.py; then echo "FAIL: the subclass bypass (_request_without_hedge_retry) is still present" >&2; exit 1; fi
grep -qi "hedge" docs/contributor-guide.md || { echo "FAIL: contributor guide does not mention the hedge" >&2; exit 1; }
grep -qi "at most one narration" docs/contributor-guide.md || { echo "FAIL: contributor guide lost its one-narration-request rule" >&2; exit 1; }
if grep -Eq '2026-[0-9]{2}-[0-9]{2}' docs/contributor-guide.md; then echo "FAIL: dated entry in the guide" >&2; exit 1; fi
"$PY" scripts/ringer/transcript_1a/live_baseline.py --route observe_park_bench_1b --enforce --replicates 3 --max-calls 240 --dry-run --out "$SCRATCH/dry" > /dev/null || { echo "FAIL: route E dry-run" >&2; exit 1; }
"$PY" scripts/ringer/environment_narration/hidden_clues_smoke_report.py "$SCRATCH/dry" > "$SCRATCH/report.txt" || { cat "$SCRATCH/report.txt"; echo "FAIL: smoke report on dry rows" >&2; exit 1; }
for g in S1 S2 S3 S4 S5 S6; do grep -q "^$g: PASS" "$SCRATCH/report.txt" || { echo "FAIL: $g not PASS on the dry run" >&2; exit 1; }; done
echo "narration hedge checks ok"
