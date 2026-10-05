#!/bin/bash
set -u
OUT=/home/bcorfman/dev/ringer-work/companion-alongside
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e packages/worldkeeper/src/worldkeeper/model.py -e storygame/runtime/item_facts.py -e 'tests/.*\.py' -e 'packages/worldkeeper/tests/.*\.py' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 packages/worldkeeper/src/worldkeeper/model.py | grep -q 'def alongside' || { echo "FAIL: World.alongside not added"; exit 1; }
git diff --cached -U0 packages/worldkeeper/src/worldkeeper/model.py | grep -q 'def spot' || { echo "FAIL: World.spot not added"; exit 1; }
git diff --cached -U0 storygame/runtime/item_facts.py | grep -q 'alongside(' || { echo "FAIL: item_facts does not use alongside"; exit 1; }
git diff --cached --name-only | grep -q 'tests/' || { echo "FAIL: no tests added"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
rc=${PIPESTATUS[0]}
[ $rc -eq 0 ] || exit $rc
if [ -d packages/worldkeeper/tests ]; then TMPDIR=/tmp uv run pytest packages/worldkeeper -q 2>&1 | tail -10; exit ${PIPESTATUS[0]}; fi
