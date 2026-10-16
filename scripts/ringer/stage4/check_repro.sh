#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev '^tests/test_recent_cue_reference\.py$')
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -qx tests/test_recent_cue_reference.py || { echo "missing test file"; exit 1; }
grep -q "xfail" tests/test_recent_cue_reference.py || { echo "reproduction must be xfail(strict=True)"; exit 1; }
grep -q "strict=True" tests/test_recent_cue_reference.py || { echo "xfail must be strict"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
out=$(PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider -rxX tests/test_recent_cue_reference.py 2>&1); rc=$?
echo "$out" | tail -15
[ $rc -eq 0 ] || { echo "pytest failed"; exit 1; }
echo "$out" | grep -qi "xfailed" || { echo "no xfailed result: the reproduction must currently fail as expected"; exit 1; }
echo "$out" | grep -qi "xpassed" && { echo "unexpected xpass"; exit 1; }
$PY/ruff check tests/test_recent_cue_reference.py && $PY/ruff format --check tests/test_recent_cue_reference.py || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage4-notes/repro.patch
test -s /home/bcorfman/dev/ringer-work/stage4-notes/repro.patch || { echo "empty patch"; exit 1; }
