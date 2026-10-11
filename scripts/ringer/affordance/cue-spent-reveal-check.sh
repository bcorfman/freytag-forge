#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/cue-spent-reveal
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e '^storygame/runtime/engine.py$' -e '^tests/' -e '^scripts/ringer/affordance/cue_eligibility_compare.py$' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
test -f tests/test_cue_spent_reveal.py || { echo "FAIL: tests/test_cue_spent_reveal.py missing"; exit 1; }
grep -q "explain_reveal" storygame/runtime/engine.py || { echo "FAIL: engine.py does not use explain_reveal"; exit 1; }
# the diff to engine.py must stay inside _cue_reveal_available and imports
extra=$(git diff --cached -U0 storygame/runtime/engine.py | grep '^@@' | wc -l)
echo "engine.py hunks: $extra"
[ "$extra" -le 3 ] || { echo "FAIL: engine.py has $extra hunks; only the import and _cue_reveal_available may change"; exit 1; }
if git diff --cached storygame/runtime/engine.py | grep '^+' | grep -n -E "1C|2B|SL-|national_detention|brandon"; then echo "FAIL: story-specific text in engine.py"; exit 1; fi
rep=$(PYTHONPATH=$PWD uv run python scripts/ringer/affordance/cue_eligibility_compare.py) || exit 1
echo "$rep" | sed -n '/^Counts/,$p' | head -12
echo "$rep" | grep -q 'CUE_SHOWN_BUT_SPENT: 0' || { echo "FAIL: report still shows CUE_SHOWN_BUT_SPENT rows"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
