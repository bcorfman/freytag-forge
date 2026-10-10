#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/eligibility-explanation
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v \
  -e '^storygame/runtime/knowledge.py$' -e '^storygame/runtime/reveal_eligibility.py$' -e '^tests/' \
  -e '^scripts/ringer/affordance/sibling_reachability.py$' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
for f in storygame/runtime/reveal_eligibility.py tests/test_reveal_eligibility.py tests/test_sibling_reachability.py scripts/ringer/affordance/sibling_reachability.py; do
  test -f "$f" || { echo "FAIL: $f missing"; exit 1; }
done
grep -q "explain_reveal" storygame/runtime/knowledge.py || { echo "FAIL: knowledge.py does not use explain_reveal"; exit 1; }
if grep -rn "3A\|3C\|SL-3\|continuity" storygame/runtime/reveal_eligibility.py; then echo "FAIL: story-specific text in runtime module"; exit 1; fi
PYTHONPATH=$PWD uv run python scripts/ringer/affordance/sibling_reachability.py | tail -40 || exit 1
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
