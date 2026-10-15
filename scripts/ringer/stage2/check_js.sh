#!/usr/bin/env bash
# usage: check_js.sh <name> <owned-regex> <test files relative to frontend/...>  (runs in the task worktree)
set -u
name=$1; owned=$2; shift 2
[ -e frontend/node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
git add -A -- . ':!frontend/node_modules' >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
[ -z "$(git diff --cached --name-only)" ] && { echo "no changes made"; exit 1; }
(cd frontend && node --test "$@" 2>&1 | tail -40; exit ${PIPESTATUS[0]}) || { echo "node tests failed"; exit 1; }
for f in $(git diff --cached --name-only | grep "\.js$"); do node --check "$f" || { echo "syntax error in $f"; exit 1; }; done
git diff --cached > /home/bcorfman/dev/ringer-work/stage2-notes/$name.patch
test -s /home/bcorfman/dev/ringer-work/stage2-notes/$name.patch || { echo "empty patch"; exit 1; }
