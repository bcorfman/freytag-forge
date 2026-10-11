#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-entry-pointer
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/plot.md -e 'tests/.*\.py' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
changed=$(git diff --cached -U0 $D/plot.md | grep '^[-+]' | grep -v '^[-+][-+]' | wc -l)
[ "$changed" -eq 2 ] || { echo "FAIL: plot.md must change exactly one line (saw $changed diff lines)"; exit 1; }
git diff --cached -U0 $D/plot.md | grep -q '^+entry_text: .*had to count\. Kristin carried the copied JANUS files\. She could check them now\.\\n\\n"$' || { echo "FAIL: new entry_text line wrong"; exit 1; }
TMPDIR=/tmp uv run python -c "
from pathlib import Path
from storygame.story_package.loader import load_story_package
p = load_story_package(Path('$D'))
t = next(s for s in p.scenes if s.metadata.scene_id == '2C').metadata.entry_text
assert t.endswith('had to count. Kristin carried the copied JANUS files. She could check them now.\n\n'), repr(t)
print('entry ok')
" || exit 1
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
