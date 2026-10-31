#!/usr/bin/env bash
# Checks for the T9h drain-rejection free tasks (P1 recorder, P1 report, P2 payloads, P3 capture). Free: no network, no model call.
# Usage: check_t9h_drain_rejection_free.sh recorder|report|payloads|capture
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
TASK="${1:-}"
SCRATCH=/tmp/t9h-drain-rejection-$TASK
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

case "$TASK" in
  recorder)
    SRC="scripts/ringer/transcript_1a/live_baseline.py"
    TESTS="tests/test_live_baseline_request_identity.py tests/test_live_baseline_evidence.py tests/test_live_baseline_enforce.py tests/test_live_baseline_scene_start.py tests/test_live_baseline_scene_state.py tests/test_live_baseline_default_output.py tests/test_hedged_request.py tests/test_narration_hedge.py"
    ;;
  report)
    SRC="scripts/ringer/environment_narration/hidden_clues_smoke_report.py"
    TESTS="tests/test_hidden_clues_smoke_report.py tests/test_enforce_drain_report.py"
    ;;
  payloads)
    SRC="tests/test_drain_scene_state_payload.py"
    TESTS="tests/test_drain_scene_state_payload.py tests/test_observation_scene_state.py tests/test_web_demo_observation_enforce.py"
    ;;
  capture)
    SRC="scripts/ringer/environment_narration/drain_details_capture.py"
    TESTS="tests/test_drain_details_capture.py tests/test_scene_1b_grounding.py tests/test_1b_spine_prompts.py"
    ;;
  *) echo "usage: check_t9h_drain_rejection_free.sh recorder|report|payloads|capture" >&2; exit 2 ;;
esac

for f in $SRC $TESTS; do [ -f "$f" ] || { echo "FAIL: missing $f" >&2; exit 1; }; done
"$PY" -m pytest -q -p no:cacheprovider --no-cov $TESTS > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check $SRC $TESTS || exit 1
"$PY" -m ruff format --check $SRC $TESTS || exit 1

if [ "$TASK" = report ]; then
  RUNBOOK=docs/testing-runbook.md
  lines=$(wc -l < "$RUNBOOK")
  git diff --numstat -- "$RUNBOOK" > "$SCRATCH/runbook.numstat"
  [ "$lines" -le 375 ] || { echo "FAIL: runbook is $lines lines; keep it short" >&2; exit 1; }
  grep -q "excluded from S1-S6" scripts/ringer/environment_narration/hidden_clues_smoke_report.py || { echo "FAIL: drain label not updated" >&2; exit 1; }
  grep -q "drain outcomes" scripts/ringer/environment_narration/hidden_clues_smoke_report.py || { echo "FAIL: 'drain outcomes' label missing" >&2; exit 1; }
fi
if [ "$TASK" = recorder ]; then
  grep -q "narration_http_prompts" scripts/ringer/transcript_1a/live_baseline.py || { echo "FAIL: legacy HTTP prompt count field missing" >&2; exit 1; }
fi
echo "drain-rejection $TASK checks ok"
