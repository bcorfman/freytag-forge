#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/holding-block
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e storygame/runtime/narration_safety.py -e data/stories/continuity-initiative/world.yaml -e data/stories/continuity-initiative/knowledge.yaml -e tests/test_narration_holding_block.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
test -s tests/test_narration_holding_block.py || { echo "FAIL: new test file missing"; exit 1; }
if git diff --cached -U0 -- storygame/runtime/narration_safety.py | grep '^+' | grep -qiE "holding|detention|rebecca|facility|broadcast"; then echo "FAIL: story word in code"; exit 1; fi
k=$(git diff --cached -U0 -- data/stories/continuity-initiative/knowledge.yaml | grep -E '^[+-][^+-]')
echo "$k"
[ "$(echo "$k" | grep -c '^-')" -le 2 ] || { echo "FAIL: knowledge.yaml changed more than the two entity_ids lines"; exit 1; }
echo "$k" | grep '^+' | grep -vq 'holding_block' && { echo "FAIL: knowledge.yaml added line without holding_block"; exit 1; }
grep -q 'id: holding_block' data/stories/continuity-initiative/world.yaml || { echo "FAIL: holding_block not declared"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
