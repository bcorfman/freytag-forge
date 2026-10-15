#!/usr/bin/env bash
# Check for astra-3ab-spine-prompts. Runs inside the Ringer worktree; no git index writes (sandbox).
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-3ab-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
bad=$(git status --porcelain | grep -v -E '^( M|M |\?\?|A |AM) (frontend/e2e/canon-journey\.js|tests/test_3ab_spine_prompts\.py)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
changed=$(git diff -U0 HEAD -- frontend/e2e/canon-journey.js | grep -E '^[+-][^+-]' || true)
[ -n "$changed" ] || { echo "FAIL canon-journey.js unchanged"; exit 1; }
echo "$changed" | grep -E '^[+-]' | grep -v -E '^[+-]\s+".*",?\s*$' && { echo "FAIL changes outside prompt strings"; exit 1; }
mkdir -p /home/bcorfman/dev/ringer-work/astra-patches 2>/dev/null
{ git diff HEAD -- frontend/e2e/canon-journey.js; git diff --no-index /dev/null tests/test_3ab_spine_prompts.py; } > /home/bcorfman/dev/ringer-work/astra-patches/step-3ab.patch 2>/dev/null || true
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not imported from worktree"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov tests/test_3ab_spine_prompts.py tests/test_1b_spine_prompts.py tests/test_2c_spine_prompts.py tests/test_canon_journey.py 2>&1 | tail -8
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL tests"; exit 1; }
$PY -m ruff check tests/test_3ab_spine_prompts.py && $PY -m ruff format --check tests/test_3ab_spine_prompts.py || exit 1
echo PASS
