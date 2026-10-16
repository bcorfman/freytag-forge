#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev '^(storygame/runtime/recent_cue\.py|tests/test_recent_cue_unit\.py)$')
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in storygame/runtime/recent_cue.py tests/test_recent_cue_unit.py; do git diff --cached --name-only | grep -qx "$f" || { echo "missing $f"; exit 1; }; done
grep -n "fullmatch\|turn_(" storygame/runtime/recent_cue.py && { echo "record id must not be parsed"; exit 1; }
git diff --cached -- tests/test_recent_cue_unit.py | grep -E '^-' | grep -E '^-\s*assert' && { echo "an existing assertion was removed"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests/test_recent_cue_reference.py tests/test_recent_cue_unit.py tests/test_1a_gap_pointer.py tests/test_established_reveal_match.py tests/test_semantic_reveal_match.py tests/test_cloudflare_transport.py 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
$PY/ruff check storygame/runtime/recent_cue.py tests/test_recent_cue_unit.py && $PY/ruff format --check storygame/runtime/recent_cue.py tests/test_recent_cue_unit.py || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage4-notes/recent-cue-fix.patch
test -s /home/bcorfman/dev/ringer-work/stage4-notes/recent-cue-fix.patch || { echo "empty patch"; exit 1; }
