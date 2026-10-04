#!/bin/bash
# Ringer check for the L2 semantic_match recording change (cwd = task worktree).
set -u
OUT=/home/bcorfman/dev/ringer-work/affordance-l2-semantic
mkdir -p "$OUT"
[ -f notes.md ] || { echo "FAIL: notes.md missing at the worktree root"; exit 1; }
cp notes.md "$OUT/notes.md"
git add -A -- . ':!notes.md' ':!frontend/node_modules' ':!frontend/test-results'
bad=$(git diff --cached --name-only | grep -v -x -e frontend/e2e/blind-player.js -e frontend/e2e/blind-player.test.js -e frontend/e2e/blind-player.spec.js || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached --quiet && { echo "FAIL: no change was made"; exit 1; }
git diff --cached > "$OUT/l2-semantic.patch"
cd frontend
[ -d node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules node_modules
node --test e2e/*.test.js 2>&1 | tail -30
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: node tests"; exit 1; }
E2E_API_BASE_URL=http://127.0.0.1:9 npx playwright test --list --grep @blind-player 2>&1 | grep -q "blind-player" || { echo "FAIL: @blind-player test not listed"; exit 1; }
grep -q "semantic_match" e2e/blind-player.spec.js || { echo "FAIL: spec never reads payload.semantic_match"; exit 1; }
grep -q "semantic_match" e2e/blind-player.test.js || { echo "FAIL: no test covers semantic_match"; exit 1; }
grep -q '"staging"' e2e/blind-player.spec.js || { echo "FAIL: staging guard lost"; exit 1; }
echo PASS
