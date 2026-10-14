#!/usr/bin/env bash
# Check for astra-cap-mismatch. Runs inside the Ringer worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-cap-mismatch-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
main_bad=$(git -C /home/bcorfman/dev/freytag-forge status --porcelain | grep -v -E "scripts/ringer/astra/" || true)
[ -z "$main_bad" ] || { echo "FAIL main checkout modified:"; echo "$main_bad"; exit 1; }
[ -e frontend/node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
git add -A -- storygame tests
bad=$(git status --porcelain | grep -v node_modules | grep -v -E '^(A|M)  (storygame/runtime/[A-Za-z0-9_]+\.py|tests/[A-Za-z0-9_./-]+\.py)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
OUT=/home/bcorfman/dev/ringer-work/astra-patches; mkdir -p "$OUT"
git diff --cached > "$OUT/cap-mismatch.patch"
[ -s "$OUT/cap-mismatch.patch" ] || { echo "FAIL empty patch"; exit 1; }
[ -f tests/test_established_reveal_match.py ] || { echo "FAIL tests/test_established_reveal_match.py missing"; exit 1; }
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not from worktree"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov tests/test_established_reveal_match.py 2>&1 | tail -12
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL the reproduction test still fails"; exit 1; }
grep -q -i "model" tests/test_established_reveal_match.py && grep -q "ineligible_selection" tests/test_established_reveal_match.py || { echo "FAIL missing negative test: a model-selected id outside projection.candidates must still raise ineligible_selection"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov -x tests 2>&1 | tail -12
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL full suite"; exit 1; }
$PY -m ruff check storygame tests && $PY -m ruff format --check storygame tests || exit 1
echo PASS
