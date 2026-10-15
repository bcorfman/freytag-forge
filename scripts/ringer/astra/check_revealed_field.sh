#!/usr/bin/env bash
# Check for astra-revealed-field. Runs inside the Ringer worktree (index writes may be blocked by the sandbox, so no git add).
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-revealed-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
bad=$(git status --porcelain | grep -v -E '^( M|M |\?\?|A |AM) (storygame/runtime/state\.py|storygame/runtime/engine\.py|tests/test_revealed_knowledge_ids\.py|tests/test_web_demo\.py)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
mkdir -p /home/bcorfman/dev/ringer-work/astra-patches
{ git diff HEAD; git diff --no-index /dev/null tests/test_revealed_knowledge_ids.py; } > /home/bcorfman/dev/ringer-work/astra-patches/revealed.patch
grep -q "revealed_knowledge_ids" storygame/runtime/state.py || { echo "FAIL field missing in state.py"; exit 1; }
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not imported from worktree"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov -n auto 2>&1 | tail -6
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL tests"; exit 1; }
$PY -m ruff check storygame tests && $PY -m ruff format --check storygame tests || exit 1
echo PASS
