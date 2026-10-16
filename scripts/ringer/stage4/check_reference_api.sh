#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
owned='^(storygame/web_demo\.py|tests/test_web_demo_clarification\.py)$'
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in storygame/web_demo.py tests/test_web_demo_clarification.py; do
  git diff --cached --name-only | grep -qx "$f" || { echo "missing deliverable $f"; exit 1; }
done
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider -n 4 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "full suite failed"; exit 1; }
F="storygame/web_demo.py tests/test_web_demo_clarification.py"
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage4-notes/reference-api.patch
test -s /home/bcorfman/dev/ringer-work/stage4-notes/reference-api.patch || { echo "empty patch"; exit 1; }
