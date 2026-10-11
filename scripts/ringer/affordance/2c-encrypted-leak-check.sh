#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-encrypted-leak
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/knowledge.yaml -e tests/test_knowledge_projection.py -e tests/test_narration_safety.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 $D/knowledge.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | grep -qE 'delivery_text|statement|cue_text|action_evidence|^[-+] *(id|requires|establishes|source|earn_when):' && { echo "FAIL: knowledge.yaml lines other than the d_r1 first must_convey group changed"; exit 1; }
TMPDIR=/tmp uv run python - <<'P' || exit 1
from pathlib import Path
from storygame.story_package.loader import load_story_package
t = load_story_package(Path("data/stories/continuity-initiative")).knowledge_indexes.term_to_knowledge
for k in ("michelle's encrypted message", "encrypted message from michelle"):
    assert "k_sl_2c_d_r1" not in t.get(k, ()), f"{k} still a leak term: {t.get(k)}"
assert "k_sl_2c_d_r1" in t.get("coded message", ()), "coded message term must be untouched"
print("terms ok")
P
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
