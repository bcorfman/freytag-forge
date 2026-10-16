#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
owned='^(storygame/runtime/recent_cue\.py|storygame/runtime/cloudflare\.py|tests/test_recent_cue_reference\.py|tests/test_recent_cue_unit\.py)$'
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in storygame/runtime/recent_cue.py storygame/runtime/cloudflare.py tests/test_recent_cue_reference.py tests/test_recent_cue_unit.py; do
  git diff --cached --name-only | grep -qx "$f" || { echo "missing deliverable $f"; exit 1; }
done
grep -q "xfail" tests/test_recent_cue_reference.py && { echo "xfail markers must be removed once the fix works"; exit 1; }
git diff --cached -- tests/test_recent_cue_reference.py | grep -E '^-' | grep -E '^-\s*assert' && { echo "an existing assertion was removed or weakened"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests/test_recent_cue_reference.py tests/test_recent_cue_unit.py tests/test_1a_gap_pointer.py tests/test_established_reveal_match.py tests/test_semantic_reveal_match.py tests/test_candidate_matcher.py tests/test_cloudflare_transport.py tests/test_cue_spent_reveal.py tests/test_reveal_universe.py tests/test_revealed_knowledge_ids.py 2>&1 | tail -20; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
$PY/ruff check storygame/runtime/recent_cue.py storygame/runtime/cloudflare.py tests/test_recent_cue_reference.py tests/test_recent_cue_unit.py && $PY/ruff format --check storygame/runtime/recent_cue.py storygame/runtime/cloudflare.py tests/test_recent_cue_reference.py tests/test_recent_cue_unit.py || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage4-notes/recent-cue.patch
test -s /home/bcorfman/dev/ringer-work/stage4-notes/recent-cue.patch || { echo "empty patch"; exit 1; }
