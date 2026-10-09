#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-detention-level
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/knowledge.yaml -e tests/test_knowledge_leakage_matrix.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
n=$(git diff --cached -U0 $D/knowledge.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | wc -l)
[ "$n" -eq 2 ] || { echo "FAIL: knowledge.yaml must change exactly one line, got $n diff lines"; exit 1; }
git diff --cached -U0 $D/knowledge.yaml | grep -q '^+.*transfer orders for captives on the detention level and a maintenance network' || { echo "FAIL: frame line not as specified"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
