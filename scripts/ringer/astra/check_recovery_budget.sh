#!/usr/bin/env bash
# Check for astra-recovery-budget. Runs inside the Ringer worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-recovery-budget-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
main_bad=$(git -C /home/bcorfman/dev/freytag-forge status --porcelain | grep -v -E "scripts/ringer/astra/|\.plans/" || true)
[ -z "$main_bad" ] || { echo "FAIL main checkout modified:"; echo "$main_bad"; exit 1; }
[ -e frontend/node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
git add -A -- storygame tests docs/testing-runbook.md
bad=$(git status --porcelain | grep -v node_modules | grep -v -E '^(A|M)  (storygame/runtime/[A-Za-z0-9_]+\.py|tests/[A-Za-z0-9_./-]+\.py|docs/testing-runbook\.md)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
OUT=/home/bcorfman/dev/ringer-work/astra-patches; mkdir -p "$OUT"
git diff --cached > "$OUT/recovery-budget.patch"
[ -s "$OUT/recovery-budget.patch" ] || { echo "FAIL empty patch"; exit 1; }
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not from worktree"; exit 1; }
T=tests/test_recovery_budget.py
[ -f "$T" ] || { echo "FAIL $T missing"; exit 1; }
for w in budget transient guard sanitiz; do
  grep -q -i "$w" "$T" || { echo "FAIL $T has no test mentioning '$w'"; exit 1; }
done
$PY -m pytest -q -p no:cacheprovider --no-cov "$T" 2>&1 | tail -15
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL authority tests"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov -x tests 2>&1 | tail -12
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL full suite"; exit 1; }
$PY -m ruff check storygame tests && $PY -m ruff format --check storygame tests || exit 1
echo PASS
