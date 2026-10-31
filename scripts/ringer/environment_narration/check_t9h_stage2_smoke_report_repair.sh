#!/usr/bin/env bash
# Check for the T9h smoke reporter and runbook repair task. Free: no network, no model call.
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
SCRIPT=scripts/ringer/environment_narration/hidden_clues_smoke_report.py
TEST=tests/test_hidden_clues_smoke_report.py
RUNBOOK=docs/testing-runbook.md
SCRATCH=/tmp/t9h-stage2-smoke-report-repair
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

"$PY" -m pytest -q -p no:cacheprovider --no-cov "$TEST" > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check "$SCRIPT" "$TEST" || exit 1
"$PY" -m ruff format --check "$SCRIPT" "$TEST" || exit 1

# The runbook sentence is replaced in place, not appended to.
if grep -q "it contains no candidate ID, candidate statement" "$RUNBOOK"; then
  echo "FAIL: old runbook sentence still present" >&2
  exit 1
fi
grep -q "text the game will append" "$RUNBOOK" || { echo "FAIL: new runbook sentence missing" >&2; exit 1; }
grep -q "complete player text after runtime composition" "$RUNBOOK" || { echo "FAIL: runbook lacks the composed-text check" >&2; exit 1; }
if grep -Eq '2026-[0-9]{2}-[0-9]{2}' "$RUNBOOK"; then echo "FAIL: dated entry added to the runbook" >&2; exit 1; fi
lines=$(wc -l < "$RUNBOOK")
[ "$lines" -le 369 ] || { echo "FAIL: runbook grew to $lines lines" >&2; exit 1; }
echo "smoke report repair checks ok"
