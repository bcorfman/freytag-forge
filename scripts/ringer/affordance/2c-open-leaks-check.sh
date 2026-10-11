#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/open-leaks
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/knowledge.yaml -e $D/world.yaml -e tests/test_knowledge_projection.py -e tests/test_narration_safety.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 $D/knowledge.yaml $D/world.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | grep -qE 'delivery_text|statement|cue_text|action_evidence|earn_when|^[-+] *(id|requires|establishes|source|name):' && { echo "FAIL: a protected field changed"; exit 1; }
TMPDIR=/tmp uv run python - <<'P' || exit 1
from pathlib import Path
from storygame.story_package.loader import load_story_package
I = load_story_package(Path("data/stories/continuity-initiative")).knowledge_indexes
for t in ("coded message", "archive crisis", "escape route"):
    assert not I.term_to_knowledge.get(t), f"{t!r} still owned: {I.term_to_knowledge.get(t)}"
assert "rebecca's desk" not in I.entity_alias_to_entities, "rebecca's desk still an entity alias"
assert "rebecca_desk" in (I.entity_alias_to_entities.get("executive desk") or ()), "executive desk must still resolve to rebecca_desk"
print("terms ok")
P
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
