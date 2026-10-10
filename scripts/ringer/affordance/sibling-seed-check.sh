#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/sibling-seed
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e '^scripts/ringer/affordance/sibling_reachability.py$' -e '^tests/test_sibling_reachability.py$' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
row=$(PYTHONPATH=$PWD uv run python scripts/ringer/affordance/sibling_reachability.py | grep '^SL-3A-B | k_sl_3a_b_r2 | k_sl_3a_b_r1')
echo "$row"
echo "$row" | grep -q '| yes |' || { echo "FAIL: 3A medical-entry row must say 'yes' (SL-3A-E supplies the fact)"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
