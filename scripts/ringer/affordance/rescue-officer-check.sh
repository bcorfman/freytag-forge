#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/rescue-officer
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/knowledge.yaml -e tests/test_narration_safety.py -e tests/test_knowledge_projection.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 $D/knowledge.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | grep -qE 'delivery_text|statement|cue_text|action_evidence|must_convey|aliases|earn_when|^[-+] *(id|requires|establishes|source):' && { echo "FAIL: only leak_terms lines may change"; exit 1; }
TMPDIR=/tmp uv run python - <<'P' || exit 1
from pathlib import Path
from storygame.story_package.loader import load_story_package
I = load_story_package(Path("data/stories/continuity-initiative")).knowledge_indexes
b, l = I.term_to_knowledge, I.leak_term_to_knowledge
assert "k_resolution_kristin_rescue" in b.get("rescue efforts", ()), "recall alias must stay"
assert "k_sl_2a_c_r1" in b.get("security officer", ()), "broad index must keep security officer"
assert "k_resolution_kristin_rescue" not in l.get("rescue efforts", ()), "rescue efforts still a leak term"
assert "k_sl_2a_c_r1" not in l.get("security officer", ()), "security officer still a leak term"
assert "k_resolution_kristin_rescue" in l.get("remaining detention sites", ()), "remaining detention sites must stay guarded"
for t in ("sensor fault", "ventilation monitor", "security supervisor", "restricted corridor access"):
    assert "k_sl_2a_c_r1" in l.get(t, ()), f"{t!r} must stay guarded"
print("indexes ok")
P
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
