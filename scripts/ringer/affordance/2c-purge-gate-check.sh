#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-purge-gate
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e data/stories/continuity-initiative/storylets.md -e data/stories/continuity-initiative/storylet-routes.yaml -e tests/test_2c_turn_one_copy.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
[ -f tests/test_2c_turn_one_copy.py ] || { echo "FAIL: new test file missing"; exit 1; }
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 data/stories/continuity-initiative/storylets.md | grep '^[-+]' | grep -v -e '^--- ' -e '^+++ ' > "$OUT/md.diff"
[ "$(cat "$OUT/md.diff")" = "-- The purge/transfer clock is active and understood." ] || { echo "FAIL: storylets.md must only lose the one bullet"; cat "$OUT/md.diff"; exit 1; }
git diff --cached -U0 data/stories/continuity-initiative/storylet-routes.yaml | grep '^[-+]' | grep -v -e '^--- ' -e '^+++ ' > "$OUT/yaml.diff"
[ "$(wc -l < "$OUT/yaml.diff")" -eq 4 ] && grep -q 'purge_clock_started' "$OUT/yaml.diff" && grep -q '^+ *conditions: \[\]$' "$OUT/yaml.diff" || { echo "FAIL: yaml must swap the 2-line condition for 'conditions: []'"; cat "$OUT/yaml.diff"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
[ "${PIPESTATUS[0]}" -eq 0 ] || exit 1
# the new test must fail without the data edits
git diff --cached -- data > "$OUT/data.patch"
git apply -R "$OUT/data.patch" || { echo "FAIL: cannot revert data edits"; exit 1; }
if TMPDIR=/tmp uv run pytest -q tests/test_2c_turn_one_copy.py -k "copy" >/tmp/2c-purge-gate-neg.out 2>&1; then
  git apply "$OUT/data.patch"; echo "FAIL: the new test passes even without the edit"; tail -5 /tmp/2c-purge-gate-neg.out; exit 1
fi
git apply "$OUT/data.patch"
echo "negative control ok: new test fails without the edit"
