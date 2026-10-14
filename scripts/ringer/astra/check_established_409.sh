#!/usr/bin/env bash
# Check for astra-established-409 (diagnosis + failing test only). Runs inside the Ringer worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-established-409-notes/diagnosis.md
[ -s "$N" ] || { echo "FAIL no diagnosis at $N"; exit 1; }
main_bad=$(git -C /home/bcorfman/dev/freytag-forge status --porcelain | grep -v -E "scripts/ringer/astra/" || true)
[ -z "$main_bad" ] || { echo "FAIL main checkout modified:"; echo "$main_bad"; exit 1; }
git add -A -- tests
bad=$(git status --porcelain | grep -v -E '^A  tests/test_established_reveal_match\.py$' || true)
[ -z "$bad" ] || { echo "FAIL stray files (tests/test_established_reveal_match.py only):"; echo "$bad"; exit 1; }
export PYTHONPATH=$PWD TMPDIR=/tmp
OUT=/home/bcorfman/dev/ringer-work/astra-patches; mkdir -p "$OUT"; git diff --cached > "$OUT/established-409-test.patch"
[ -s "$OUT/established-409-test.patch" ] || { echo "FAIL no test file"; exit 1; }
grep -q -i -E "file.*line|\.py:[0-9]+" "$N" || { echo "FAIL diagnosis names no file:line"; exit 1; }
# The new test must FAIL on current code, and fail with the 409 code, not an import or setup error.
$PY -m pytest -q -p no:cacheprovider --no-cov tests/test_established_reveal_match.py > /tmp/established409.out 2>&1
rc=$?
tail -25 /tmp/established409.out
[ $rc -ne 0 ] || { echo "FAIL the test passes on current code, so it does not reproduce the defect"; exit 1; }
grep -q "ineligible_selection" /tmp/established409.out || { echo "FAIL test fails but not with ineligible_selection"; exit 1; }
$PY -m ruff check tests/test_established_reveal_match.py && $PY -m ruff format --check tests/test_established_reveal_match.py || exit 1
echo PASS
