#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2a-forms-verb
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e "^$D/knowledge.yaml$" -e '^tests/' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
n=$(git diff --cached -U0 $D/knowledge.yaml | grep '^[-+]' | grep -vc '^[-+][-+]')
echo "knowledge.yaml changed lines: $n"
[ "$n" -eq 2 ] || { echo "FAIL: knowledge.yaml must change exactly one line (2 diff lines)"; exit 1; }
git diff --cached -U0 $D/knowledge.yaml | grep '^+  - \[prepare, draft' | grep -q 'hand over, ask\]\|ask,' || { echo "FAIL: ask not added to the k_sl_2a_b_r2 verb line"; exit 1; }
test -f tests/test_2a_forms_words.py || { echo "FAIL: tests/test_2a_forms_words.py missing"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
