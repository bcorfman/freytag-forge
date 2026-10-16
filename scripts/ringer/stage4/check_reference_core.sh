#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
owned='^(storygame/runtime/reference_resolution\.py|storygame/runtime/engine\.py|tests/test_reference_resolution\.py|tests/test_reference_clarification\.py)$'
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in storygame/runtime/reference_resolution.py storygame/runtime/engine.py tests/test_reference_resolution.py tests/test_reference_clarification.py; do
  git diff --cached --name-only | grep -qx "$f" || { echo "missing deliverable $f"; exit 1; }
done
git diff --cached -- storygame/runtime/engine.py | grep -E '^-' | grep -vE '^---' | grep -E 'def turn|def _turn_active' && { echo "turn/_turn_active signature lines removed; keep them backward compatible"; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider -n 4 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "full suite failed"; exit 1; }
F="storygame/runtime/reference_resolution.py storygame/runtime/engine.py tests/test_reference_resolution.py tests/test_reference_clarification.py"
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage4-notes/reference-core.patch
test -s /home/bcorfman/dev/ringer-work/stage4-notes/reference-core.patch || { echo "empty patch"; exit 1; }
