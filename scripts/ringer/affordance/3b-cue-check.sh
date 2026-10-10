#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/3b-cue
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/handoffs.yaml -e $D/plot.md -e tests/test_markdown_story_package.py -e tests/test_canon_journey.py -e bench/affordance_known_gaps.json || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
n=$(git diff --cached -U0 $D/handoffs.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | wc -l)
[ "$n" -eq 2 ] || { echo "FAIL: handoffs.yaml must change exactly one line (got $n changed lines)"; exit 1; }
git diff --cached -U0 $D/handoffs.yaml | grep -q '^+  cue_text: JANUS tracks Kristin. The inspection console in the infrastructure corridors can send false water-pressure alarms into empty service corridors.$' || { echo "FAIL: new cue_text not exact"; exit 1; }
p=$(git diff --cached -U0 $D/plot.md | grep '^[-+]' | grep -v '^[-+][-+]')
[ "$p" = "+The inspection console is in the infrastructure corridors." ] || { echo "FAIL: plot.md must add only the one sentence line"; echo "$p"; exit 1; }
TMPDIR=/tmp uv run python scripts/ringer/affordance/3b-wording-score.py || exit 1
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
