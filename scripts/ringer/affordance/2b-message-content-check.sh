#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2b-message-content
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e data/stories/continuity-initiative/plot.md -e data/stories/continuity-initiative/knowledge.yaml -e 'tests/.*\.py' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
K=data/stories/continuity-initiative/knowledge.yaml
P=data/stories/continuity-initiative/plot.md
git diff --cached -U0 $K | grep '^[-+]' | grep -v '^[-+][-+]' > "$OUT/knowledge.diff"
[ "$(grep -c '^-' "$OUT/knowledge.diff")" -eq 2 ] && [ "$(grep -c '^+' "$OUT/knowledge.diff")" -eq 2 ] || { echo "FAIL: knowledge.yaml must change exactly the statement and delivery_text lines of k_sl_2b_c_r2"; cat "$OUT/knowledge.diff"; exit 1; }
grep -qF '“The prisoners are ready to rise up.”' "$OUT/knowledge.diff" || { echo "FAIL: curly-quoted message missing"; exit 1; }
grep -qF 'Michelle’s coded maintenance messages show she has organized prisoners to prepare an uprising from inside. A decoded message reads: “The prisoners are ready to rise up.”' "$OUT/knowledge.diff" || { echo "FAIL: statement not as specified"; exit 1; }
grep -qF "Michelle has organized prisoners. She is preparing an uprising from inside. A decoded message reads: “The prisoners are ready to rise up.” Brandon's earlier messages are still open on the remote terminal." "$OUT/knowledge.diff" || { echo "FAIL: delivery_text not as specified"; exit 1; }
git diff --cached -U0 $P | grep '^[-+]' | grep -v '^[-+][-+]' > "$OUT/plot.diff"
[ "$(grep -c '^-' "$OUT/plot.diff")" -eq 0 ] && [ "$(grep -c '^+' "$OUT/plot.diff")" -le 2 ] || { echo "FAIL: plot.md must only add the sentence (and at most one blank line)"; cat "$OUT/plot.diff"; exit 1; }
grep -qxF '+A decoded message reads: “The prisoners are ready to rise up.”' "$OUT/plot.diff" || { echo "FAIL: plot sentence missing"; exit 1; }
! grep -qi 'phase' "$OUT/knowledge.diff" "$OUT/plot.diff" || { echo "FAIL: the word phase appears in the added text"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
