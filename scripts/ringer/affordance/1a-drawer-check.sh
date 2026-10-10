#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/1a-drawer
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e "^$D/knowledge.yaml$" -e "^$D/handoffs.yaml$" -e '^tests/' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
for f in knowledge.yaml handoffs.yaml; do
  n=$(git diff --cached -U0 $D/$f | grep '^[-+]' | grep -vc '^[-+][-+]')
  echo "$f changed lines: $n"
  [ "$n" -le 4 ] || { echo "FAIL: $f diff larger than the approved lines"; exit 1; }
done
grep -q 'lower edge, bottom edge' $D/knowledge.yaml || { echo "FAIL: evidence line missing"; exit 1; }
grep -q 'beneath its lower edge is wide enough' $D/handoffs.yaml || { echo "FAIL: cue text missing"; exit 1; }
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
