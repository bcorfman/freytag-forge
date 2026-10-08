#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/leak-names
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e data/stories/continuity-initiative/knowledge.yaml -e 'tests/.*\.py' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/b.patch"
d=$(git diff --cached -U0 -- data/stories/continuity-initiative/knowledge.yaml | grep -E '^[+-][^+-]')
echo "$d"
n=$(echo "$d" | grep -c .)
[ "$n" -le 2 ] || { echo "FAIL: more than one line of knowledge.yaml changed"; exit 1; }
grep -q '\[they have access to the facility\]' data/stories/continuity-initiative/knowledge.yaml || { echo "FAIL: new group missing"; exit 1; }
if grep -n '\[gaining access to the facility\|, access to the facility\|\[access to the facility' data/stories/continuity-initiative/knowledge.yaml; then echo "FAIL: short variants still present"; exit 1; fi
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
