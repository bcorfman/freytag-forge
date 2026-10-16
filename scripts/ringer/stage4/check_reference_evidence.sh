#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev '^(storygame/runtime/cloudflare\.py|storygame/runtime/reference_resolution\.py|tests/test_reference_evidence_append\.py)$')
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -qx 'tests/test_reference_evidence_append.py' || { echo "missing new test file"; exit 1; }
git diff --cached --name-only | grep -qx 'storygame/runtime/cloudflare.py' || { echo "cloudflare.py unchanged"; exit 1; }
git diff --cached -- storygame tests | grep -E '^-\s*assert' && { echo "an existing assertion was removed"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
F="storygame/runtime/cloudflare.py storygame/runtime/reference_resolution.py tests/test_reference_evidence_append.py"
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
mkdir -p /home/bcorfman/dev/ringer-work/stage4-notes
git diff --cached > /home/bcorfman/dev/ringer-work/stage4-notes/reference-evidence.patch
test -s /home/bcorfman/dev/ringer-work/stage4-notes/reference-evidence.patch || { echo "empty patch"; exit 1; }
