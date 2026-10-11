#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/leak-terms
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/knowledge.yaml -e storygame/story_package/models.py -e storygame/story_package/loader.py -e storygame/runtime/narration_safety.py -e docs/markdown-story-authoring.md -e docs/world-model-grounding.md -e tests/test_leak_terms.py -e tests/test_knowledge_projection.py -e tests/test_narration_safety.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 $D/knowledge.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | grep -qE 'delivery_text|statement|cue_text|action_evidence|earn_when|^[-+] *(id|requires|establishes|source):' && { echo "FAIL: a protected knowledge field changed"; exit 1; }
TMPDIR=/tmp uv run python - <<'P' || exit 1
from pathlib import Path
from storygame.story_package.loader import load_story_package
I = load_story_package(Path("data/stories/continuity-initiative")).knowledge_indexes
broad, leak = dict(I.term_to_knowledge), dict(I.leak_term_to_knowledge)
for t, owners in {"coded message": {"k_sl_2c_d_r1", "k_sl_2c_d_r2"}, "michelle's encrypted message": {"k_sl_2c_d_r1"}, "encrypted message from michelle": {"k_sl_2c_d_r1"}, "archive crisis": {"k_bridge_2b_archive_crisis"}, "escape route": {"k_scene_3c_entry"}}.items():
    assert owners <= set(broad.get(t, ())), f"{t!r} must be a recall/grounding term again: {broad.get(t)}"
    assert not owners & set(leak.get(t, ())), f"{t!r} must not be a leak term: {leak.get(t)}"
extra = {t for t in leak if t not in broad}
assert not extra, f"leak terms not in the broad index: {extra}"
for t in ("maintenance access route", "rebecca's secured office", "open the detention cells"):
    assert "k_sl_2c_d_r1" in leak.get(t, ()), f"{t!r} must stay a guarded leak term"
print("indexes ok")
P
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q --cov --cov-report=term:skip-covered 2>&1 | tail -30
exit ${PIPESTATUS[0]}
