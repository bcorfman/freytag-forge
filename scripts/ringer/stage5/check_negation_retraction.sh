#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev '^(storygame/runtime/candidate_matcher\.py|tests/test_negation_scope\.py)$')
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in storygame/runtime/candidate_matcher.py tests/test_negation_scope.py; do git diff --cached --name-only | grep -qx "$f" || { echo "missing change in $f"; exit 1; }; done
git diff --cached -- storygame tests | grep -E '^-\s*assert' && { echo "an existing assertion was removed"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python - <<'PYEOF' || { echo "retraction expectations failed"; exit 1; }
from storygame.runtime.candidate_matcher import negation_scoped_command as n
blocked = ["Open the drawer, never mind.", "Open the drawer, no wait.", "Open the drawer, no stop.", "Open the drawer, don't bother.",
           "Open the drawer, nevermind.", "Open the drawer, forget it, don't.", "Open the drawer, no, cancel that.", "Open the drawer, don't, hold on.",
           "Do not open the drawer.", "Open the drawer, don't open it.", "Open the drawer, don't."]
allowed = {"Open the drawer, but do not take anything yet.": "Open the drawer", "Check the copied JANUS files, but do not send anything yet.": "Check the copied JANUS files",
           "Open the drawer but not the cabinet.": "Open the drawer", "Search the room without touching the safe.": "Search the room"}
for s in blocked:
    assert n(s) is None, f"must stay blocked: {s!r} -> {n(s)!r}"
for s, want in allowed.items():
    assert n(s) == want, f"must stay allowed: {s!r} -> {n(s)!r}"
PYEOF
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
F="storygame/runtime/candidate_matcher.py tests/test_negation_scope.py"
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
mkdir -p /home/bcorfman/dev/ringer-work/stage5-notes
git diff --cached > /home/bcorfman/dev/ringer-work/stage5-notes/negation-retraction.patch
test -s /home/bcorfman/dev/ringer-work/stage5-notes/negation-retraction.patch || { echo "empty patch"; exit 1; }
