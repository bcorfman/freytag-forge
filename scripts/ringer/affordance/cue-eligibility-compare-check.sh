#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/cue-eligibility-compare
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e '^scripts/ringer/affordance/cue_eligibility_compare.py$' -e '^tests/test_cue_eligibility_compare.py$' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
rep=$(PYTHONPATH=$PWD uv run python scripts/ringer/affordance/cue_eligibility_compare.py) || exit 1
echo "$rep" | tail -25
echo "$rep" | grep -q 'CUE_SHOWN_BUT_SPENT' || { echo "FAIL: report never shows CUE_SHOWN_BUT_SPENT"; exit 1; }
echo "$rep" | grep -E '1A.*continuity_initiative_known.*CUE_SHOWN_BUT_SPENT|CUE_SHOWN_BUT_SPENT.*1A.*continuity_initiative_known' >/dev/null || { echo "FAIL: known 1A case (continuity_initiative_known after SL-1A-B fired) not reported as CUE_SHOWN_BUT_SPENT"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
