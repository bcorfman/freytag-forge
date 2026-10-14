#!/usr/bin/env bash
# Check for astra-guard-retry-flag. Runs inside the Ringer worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-guard-retry-flag-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
main_bad=$(git -C /home/bcorfman/dev/freytag-forge status --porcelain | grep -v -E "scripts/ringer/astra/" || true)
[ -z "$main_bad" ] || { echo "FAIL main checkout modified:"; echo "$main_bad"; exit 1; }
[ -e frontend/node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
git add -A -- storygame tests frontend/e2e
bad=$(git status --porcelain | grep -v node_modules | grep -v -E '^(A|M)  (storygame/runtime/(state|engine|knowledge_audit)\.py|frontend/e2e/[A-Za-z0-9_.-]+\.(js)|tests/[A-Za-z0-9_./-]+\.py)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
OUT=/home/bcorfman/dev/ringer-work/astra-patches; mkdir -p "$OUT"
git diff --cached > "$OUT/guard-retry-flag.patch"
[ -s "$OUT/guard-retry-flag.patch" ] || { echo "FAIL empty patch"; exit 1; }
grep -q "guard_retry_used" storygame/runtime/state.py || { echo "FAIL TurnDelivery lacks guard_retry_used"; exit 1; }
grep -q "guard_retry" frontend/e2e/scene-runtime.spec.js || { echo "FAIL spine telemetry lacks guard retry count"; exit 1; }
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not from worktree"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov -x tests 2>&1 | tail -15
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL pytest"; exit 1; }
(cd frontend && node --check e2e/scene-runtime.spec.js && node --test e2e/*.test.js 2>&1 | tail -8; [ "${PIPESTATUS[0]}" -eq 0 ]) || { echo "FAIL node"; exit 1; }
$PY -m ruff check storygame tests && $PY -m ruff format --check storygame tests || exit 1
echo PASS
