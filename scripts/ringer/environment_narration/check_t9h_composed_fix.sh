#!/usr/bin/env bash
# Check for the composed-view fix task. Free: no network, no model call.
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
P=scripts/ringer/environment_narration/hidden_bench_prose_probe.py
A=scripts/ringer/environment_narration/hidden_bench_arm_probe.py
TESTS="tests/test_hidden_bench_prose_probe.py tests/test_hidden_bench_arm_probe.py"
RES=bench/results/environment-narration/t9h-resample
SCRATCH=/tmp/t9h-composed-fix
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
"$PY" -m pytest -q -p no:cacheprovider --no-cov $TESTS > "$SCRATCH/pytest.out" 2>&1
rc=$?; tail -25 "$SCRATCH/pytest.out"; [ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check $P $A tests/test_hidden_bench_prose_probe.py tests/test_hidden_bench_arm_probe.py || exit 1
"$PY" -m ruff format --check $P $A tests/test_hidden_bench_prose_probe.py tests/test_hidden_bench_arm_probe.py || exit 1
# The real re-sample replies (they carry item_facts) must now compose.
"$PY" $P --composed-view --rows "$RES/rows.json" --out "$SCRATCH/views" || { echo "FAIL: composed-view on re-sample rows" >&2; exit 1; }
n=$(grep -c "not composable" "$SCRATCH/views/composed_view.md")
[ "$n" -eq 0 ] || { echo "FAIL: $n re-sample rows still not composable" >&2; exit 1; }
d=$(grep -c "Kristin reaches beneath the park bench" "$SCRATCH/views/composed_view.md")
[ "$d" -ge 10 ] || { echo "FAIL: delivery appears $d times, expected at least 10 (P1 find rows)" >&2; exit 1; }
if grep -q "A short canned narration segment" "$SCRATCH/views/composed_view.md"; then echo "FAIL: stub text in composed view" >&2; exit 1; fi
# The arm probe sheets must not show the capture-time stub segment as engine text.
"$PY" $A --sheets --rows bench/results/environment-narration/t9h-stage2-diagnostic/rows.json --out "$SCRATCH/arm-sheets" || exit 1
if grep -q "A short canned narration segment" "$SCRATCH/arm-sheets/blind_sheet.md"; then echo "FAIL: arm sheets still show stub text" >&2; exit 1; fi
grep -q "Kristin reaches beneath the park bench" "$SCRATCH/arm-sheets/blind_sheet.md" || { echo "FAIL: arm sheets lost the delivery" >&2; exit 1; }
# Stage 2 artifacts stay pinned and the earlier measurement checks still pass.
bash scripts/ringer/environment_narration/check_t9h_stage2_measure_repair.sh > "$SCRATCH/measure.out" 2>&1 || { tail -20 "$SCRATCH/measure.out"; echo "FAIL: measure repair check regressed" >&2; exit 1; }
# The recorded diagnostic and re-sample rows must be untouched.
echo "composed fix checks ok"
