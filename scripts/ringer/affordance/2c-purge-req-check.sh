#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-purge-req
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e data/stories/continuity-initiative/knowledge.yaml -e 'tests/.*\.py' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 data/stories/continuity-initiative/knowledge.yaml | grep '^[-+]' | grep -v '^[-+][-+]' > "$OUT/k.diff"
[ "$(grep -c '^+' "$OUT/k.diff")" -eq 0 ] || { echo "FAIL: knowledge.yaml must only lose lines"; cat "$OUT/k.diff"; exit 1; }
[ "$(grep -c 'fact_id: purge_clock_started' "$OUT/k.diff")" -eq 2 ] || { echo "FAIL: expected exactly 2 purge_clock_started lines removed"; cat "$OUT/k.diff"; exit 1; }
[ "$(wc -l < "$OUT/k.diff")" -eq 4 ] || { echo "FAIL: expected 4 removed lines (fact_id + equals, twice)"; cat "$OUT/k.diff"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
