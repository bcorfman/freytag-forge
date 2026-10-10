#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/cue-compare-fix
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e '^scripts/ringer/affordance/cue_eligibility_compare.py$' -e '^tests/test_cue_eligibility_compare.py$' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
rep=$(PYTHONPATH=$PWD uv run python scripts/ringer/affordance/cue_eligibility_compare.py) || exit 1
echo "$rep" | tail -20
n=$(echo "$rep" | grep -c '| CUE_SHOWN_BUT_SPENT$')
[ "$n" = 3 ] || { echo "FAIL: expected exactly 3 CUE_SHOWN_BUT_SPENT table rows, got $n"; exit 1; }
for f in national_detention_network_known brandon_janus_role_known brandon_claimed_reform_motive; do
  echo "$rep" | grep '| CUE_SHOWN_BUT_SPENT$' | grep -q "$f" || { echo "FAIL: real case $f missing"; exit 1; }
done
echo "$rep" | grep -q 'NOT_STAGEABLE_FACT_TRUE' || { echo "FAIL: NOT_STAGEABLE_FACT_TRUE class missing"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
