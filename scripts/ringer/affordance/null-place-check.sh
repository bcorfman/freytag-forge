#!/bin/bash
# Ringer check: runs in the task worktree (cwd). usage: null-place-check.sh <label> <source file> <test file>
set -u
LABEL="$1"; SRC="$2"; TEST="$3"
OUT=/home/bcorfman/dev/ringer-work/null-place
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e "$SRC" -e "$TEST" || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
[ -f "$TEST" ] || { echo "FAIL: $TEST missing"; exit 1; }
git diff --cached "$SRC" | grep -q . || { echo "FAIL: $SRC unchanged"; exit 1; }
git diff --cached > "$OUT/$LABEL.patch"
# the new test must fail on the original source
cp "$SRC" /tmp/null-place-$LABEL.fixed
git show HEAD:"$SRC" > "$SRC"
if TMPDIR=/tmp uv run pytest -q "$TEST" >/tmp/null-place-$LABEL.before 2>&1; then echo "FAIL: new test passes on the ORIGINAL code, so it does not reproduce the bug"; cp /tmp/null-place-$LABEL.fixed "$SRC"; exit 1; fi
cp /tmp/null-place-$LABEL.fixed "$SRC"
TMPDIR=/tmp uv run pytest -q "$TEST" 2>&1 | tail -15; [ "${PIPESTATUS[0]}" = 0 ] || exit 1
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
