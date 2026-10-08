#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/leak-names
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e storygame/runtime/narration_safety.py -e tests/test_narration_place_names.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/a.patch"
test -s tests/test_narration_place_names.py || { echo "FAIL: new test file missing"; exit 1; }
if git diff --cached -U0 -- storygame/runtime/narration_safety.py | grep '^+' | grep -qiE "broadcast|detention|rebecca|facility|executive"; then echo "FAIL: story word in code"; exit 1; fi
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
