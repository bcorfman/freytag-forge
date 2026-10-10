#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/gates-scope
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e "^$D/plot.md$" -e '^tests/' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
changed=$(git diff --cached -U0 $D/plot.md | grep '^[-+]' | grep -v '^[-+][-+]')
nadd=$(echo "$changed" | grep -c '^+')
nrem=$(echo "$changed" | grep -c '^-')
echo "$changed"
# 3A and 3B each: item_ids line changes (1 removed, 1 added) and one new placement line; no other edits
[ "$nadd" -le 6 ] && [ "$nrem" -le 2 ] || { echo "FAIL: plot.md diff is larger than the two scene frontmatters (+$nadd -$nrem)"; exit 1; }
uv run python -I - <<'PY' || exit 1
from pathlib import Path
from storygame.story_package.loader import load_story_package
p = load_story_package(Path("data/stories/continuity-initiative"))
for sid in ("3A", "3B", "3C"):
    m = next(s for s in p.scenes if s.metadata.scene_id == sid).metadata
    if "emergency_surface_gates" not in m.item_ids: print("FAIL: not in item_ids of", sid); raise SystemExit(1)
    if "emergency_surface_gates" not in m.item_placements: print("FAIL: no placement in", sid); raise SystemExit(1)
for sid in ("1A", "1B", "1C", "2A", "2B", "2C"):
    m = next(s for s in p.scenes if s.metadata.scene_id == sid).metadata
    if "emergency_surface_gates" in m.item_ids: print("FAIL: gates leaked into", sid); raise SystemExit(1)
print("OK: gates placed in 3A, 3B, 3C and nowhere earlier")
PY
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
