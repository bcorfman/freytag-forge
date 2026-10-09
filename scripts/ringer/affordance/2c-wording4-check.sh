#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-wording4
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/knowledge.yaml -e bench/affordance_known_gaps.json -e tests/test_markdown_story_package.py -e tests/test_canon_journey.py -e scripts/ringer/affordance/2c-wording-score.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 $D/knowledge.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | grep -qE 'delivery_text|statement|cue_text|^[-+] *(id|requires|establishes|source):' && { echo "FAIL: knowledge.yaml lines other than action_evidence/earn_when changed"; git diff --cached -U0 $D/knowledge.yaml | grep -E 'delivery_text|statement|cue_text'; exit 1; }
TMPDIR=/tmp uv run python scripts/ringer/affordance/2c-wording-score.py || exit 1
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
