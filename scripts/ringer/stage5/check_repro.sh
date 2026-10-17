#!/usr/bin/env bash
# usage: check_repro.sh <test-file> <notes-file>
set -u
T="$1"; N="$2"
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Fvx "$T")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -Fqx "$T" || { echo "missing $T"; exit 1; }
test -s "$N" || { echo "missing notes $N"; exit 1; }
grep -qi "^## Verdict" "$N" && grep -qi "^## Findings" "$N" || { echo "notes need '## Findings' and '## Verdict' headings"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider "$T" 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
$PY/ruff check "$T" && $PY/ruff format --check "$T" || { echo ruff; exit 1; }
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests 2>&1 | tail -3; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "full suite failed"; exit 1; }
git diff --cached > "/home/bcorfman/dev/ringer-work/stage5-notes/$(basename "$T" .py).patch"
