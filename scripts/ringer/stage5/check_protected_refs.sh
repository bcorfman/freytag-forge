#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
OWN='^(storygame/runtime/reference_resolution\.py|storygame/runtime/knowledge\.py|tests/test_reference_protected\.py)$'
bad=$(git diff --cached --name-only | grep -Ev "$OWN")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -qx "tests/test_reference_protected.py" || { echo "missing tests/test_reference_protected.py"; exit 1; }
git diff --cached --name-only | grep -qx "storygame/runtime/reference_resolution.py" || { echo "reference_resolution.py unchanged"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
F=$(git diff --cached --name-only | grep '\.py$' | tr '\n' ' ')
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage5-notes/protected-refs.patch
test -s /home/bcorfman/dev/ringer-work/stage5-notes/protected-refs.patch || { echo "empty patch"; exit 1; }
