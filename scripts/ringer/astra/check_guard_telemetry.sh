#!/usr/bin/env bash
# Check for astra-guard-retry-measurement telemetry task. Runs inside the Ringer worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-guard-telemetry-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
main_bad=$(git -C /home/bcorfman/dev/freytag-forge status --porcelain | grep -v -E "scripts/ringer/astra/|\.plans/" || true)
[ -z "$main_bad" ] || { echo "FAIL main checkout modified:"; echo "$main_bad"; exit 1; }
git add -A -- storygame bench tests
bad=$(git status --porcelain | grep -v node_modules | grep -v -E '^(A|M)  (storygame/runtime/engine\.py|bench/core\.py|bench/guard_retry_report\.py|tests/test_guard_retry_telemetry\.py)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
OUT=/home/bcorfman/dev/ringer-work/astra-patches; mkdir -p "$OUT"
git diff --cached > "$OUT/guard-telemetry.patch"
[ -s "$OUT/guard-telemetry.patch" ] || { echo "FAIL empty patch"; exit 1; }
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not from worktree"; exit 1; }
for w in guard_retry_used guard_rejections; do
  grep -q "$w" bench/core.py || { echo "FAIL bench/core.py lacks $w"; exit 1; }
done
grep -q "last_guard_rejections" storygame/runtime/engine.py || { echo "FAIL engine lacks last_guard_rejections"; exit 1; }
for w in rescue zero committed_after_retry failed_after_retry; do
  grep -q -i "$w" tests/test_guard_retry_telemetry.py || { echo "FAIL tests lack '$w'"; exit 1; }
done
$PY -m pytest -q -p no:cacheprovider --no-cov tests/test_guard_retry_telemetry.py 2>&1 | tail -15
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL new tests"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov -x tests 2>&1 | tail -12
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL full suite"; exit 1; }
$PY -m ruff check storygame bench tests && $PY -m ruff format --check storygame bench tests || exit 1
echo PASS
