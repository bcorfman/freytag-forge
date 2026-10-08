#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/required-closure
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e storygame/story_package/obligations.py -e tests/test_required_storylet_closure.py -e tests/test_reveal_prerequisites.py -e storygame/personas.py -e tests/test_personas.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
