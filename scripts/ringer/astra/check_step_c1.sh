#!/usr/bin/env bash
# Check for astra-step-c1-2c-prompt. Runs inside the Ringer worktree. The git-index steps may fail in the sandbox; use SKIP_GIT=1 for the orchestrator rerun-free path.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-step-c1-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
bad=$(git status --porcelain | grep -v -E '^( M|M |\?\?|A |AM) (frontend/e2e/canon-journey\.js|tests/test_2c_spine_prompts\.py)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
changed=$(git diff -U0 HEAD -- frontend/e2e/canon-journey.js | grep -E '^[+-][^+-]' || true)
[ "$(echo "$changed" | wc -l)" -eq 2 ] || { echo "FAIL expected one removed and one added line in canon-journey.js:"; echo "$changed"; exit 1; }
echo "$changed" | grep -q 'Read Michelle'"'"'s coded message and commit to the plan it describes\.' || { echo "FAIL new prompt text wrong"; exit 1; }
mkdir -p /home/bcorfman/dev/ringer-work/astra-patches
{ git diff HEAD -- frontend/e2e/canon-journey.js; git diff --no-index /dev/null tests/test_2c_spine_prompts.py; } > /home/bcorfman/dev/ringer-work/astra-patches/step-c1.patch
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not imported from worktree"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov tests/test_2c_spine_prompts.py tests/test_2c_assess_verbs.py tests/test_2c_assess_engine_turn.py tests/test_canon_journey.py 2>&1 | tail -8
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL tests"; exit 1; }
$PY -m ruff check tests/test_2c_spine_prompts.py && $PY -m ruff format --check tests/test_2c_spine_prompts.py || exit 1
echo PASS
