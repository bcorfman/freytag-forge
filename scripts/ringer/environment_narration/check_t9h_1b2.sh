#!/usr/bin/env bash
# Check for the 1B.2 prompt-exposure task. Free: no network, no model call.
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
S=scripts/ringer/environment_narration/hidden_bench_1b2_capture.py
T=tests/test_hidden_bench_1b2_capture.py
SCRATCH=/tmp/t9h-1b2
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
test -f "$S" && test -f "$T" || { echo "FAIL: script or test missing" >&2; exit 1; }
"$PY" -m pytest -q -p no:cacheprovider --no-cov "$T" > "$SCRATCH/pytest.out" 2>&1
rc=$?; tail -25 "$SCRATCH/pytest.out"; [ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check "$S" "$T" || exit 1
"$PY" -m ruff format --check "$S" "$T" || exit 1
# The capture reports a finding with exit 1 (exposure) or 0 (none); anything else is a broken tool.
"$PY" "$S" --out "$SCRATCH/report.md"
rc=$?
[ $rc -le 1 ] || { echo "FAIL: capture exited $rc" >&2; exit 1; }
test -s "$SCRATCH/report.md" || { echo "FAIL: no report written" >&2; exit 1; }
for input in "Ask the man about Michelle" "Show Michelle's photograph to the man" "Inspect the park bench"; do
  grep -q "$input" "$SCRATCH/report.md" || { echo "FAIL: report lacks input: $input" >&2; exit 1; }
done
grep -qi "unrecovered" "$SCRATCH/report.md" && grep -qi "recovered" "$SCRATCH/report.md" || { echo "FAIL: report lacks both world states" >&2; exit 1; }
echo "1b2 capture exit code was $rc; 1b2 checks ok"
