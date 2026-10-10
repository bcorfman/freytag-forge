#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/1a-plot-line
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e "^$D/plot.md$" -e '^tests/' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
changed=$(git diff --cached -U0 $D/plot.md | grep '^[-+]' | grep -v '^[-+][-+]')
echo "$changed"
[ "$(echo "$changed" | grep -c '^+')" -eq 1 ] && [ "$(echo "$changed" | grep -c '^-')" -eq 1 ] || { echo "FAIL: plot.md must change exactly one line"; exit 1; }
grep -qxF "The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers." $D/plot.md || { echo "FAIL: new sentence missing"; exit 1; }
grep -q 'thin gap along its lower edge' $D/plot.md && { echo "FAIL: old sentence remains"; exit 1; }
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
