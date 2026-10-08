#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/opening-retry
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e storygame/runtime/engine.py -e tests/test_opening_retry.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 storygame/runtime/engine.py | grep -q '^+' || { echo "FAIL: engine.py not changed"; exit 1; }
test -f tests/test_opening_retry.py || { echo "FAIL: tests/test_opening_retry.py missing"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
