#!/usr/bin/env bash
# usage: check_owned.sh <name> <owned-regex> <test files...>   (runs in the task worktree)
set -u
name=$1; owned=$2; shift 2
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
export TMPDIR=/tmp
git add -A >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
[ -z "$(git diff --cached --name-only)" ] && { echo "no changes made"; exit 1; }
for t in "$@"; do test -f "$t" || { echo "missing test file $t"; exit 1; }; done
PYTHONPATH=$PWD $PY -m pytest -q --no-cov -p no:cacheprovider "$@" 2>&1 | tail -30
PYTHONPATH=$PWD $PY -m pytest -q --no-cov -p no:cacheprovider "$@" >/dev/null 2>&1 || { echo "pytest failed"; exit 1; }
files=$(git diff --cached --name-only | grep '\.py$')
$PY -m ruff check $files && $PY -m ruff format --check $files || exit 1
git diff --cached > /home/bcorfman/dev/ringer-work/stage2-notes/$name.patch
test -s /home/bcorfman/dev/ringer-work/stage2-notes/$name.patch || { echo "empty patch"; exit 1; }
