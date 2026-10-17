#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
OWN='^(data/stories/continuity-initiative/|tests/|\.plans/|docs/)'
bad=$(git diff --cached --name-only | grep -Ev "$OWN")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -qx "tests/test_guard_vocabulary.py" || { echo "missing tests/test_guard_vocabulary.py"; exit 1; }
git diff --cached --name-only | grep -qx "data/stories/continuity-initiative/world.yaml" || { echo "world.yaml unchanged"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
F=$(git diff --cached --name-only | grep '\.py$' | tr '\n' ' ')
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage5-notes/guard-vocab.patch
test -s /home/bcorfman/dev/ringer-work/stage5-notes/guard-vocab.patch || { echo "empty patch"; exit 1; }
