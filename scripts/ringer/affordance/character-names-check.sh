#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/character-names
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e storygame/runtime/narration_safety.py -e tests/test_narration_character_names.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 storygame/runtime/narration_safety.py | grep -q '^+' || { echo "FAIL: narration_safety.py not changed"; exit 1; }
test -f tests/test_narration_character_names.py || { echo "FAIL: tests/test_narration_character_names.py missing"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
