#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-rebecca
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e data/stories/continuity-initiative/plot.md -e 'tests/.*\.py' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 data/stories/continuity-initiative/plot.md | grep '^[-+]' | grep -v '^[-+][-+]' > "$OUT/plot.diff"
[ "$(wc -l < "$OUT/plot.diff")" -eq 2 ] || { echo "FAIL: plot.md must change exactly one line"; cat "$OUT/plot.diff"; exit 1; }
grep -q '^+participant_ids: \[kristin, brandon, michelle, rebecca\]$' "$OUT/plot.diff" || { echo "FAIL: line not as specified"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
