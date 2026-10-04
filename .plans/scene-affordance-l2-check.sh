#!/bin/bash
# Ringer check for L1 (cwd = task worktree).
set -u
OUT=/home/bcorfman/dev/ringer-work/affordance-l2
mkdir -p "$OUT"
[ -f notes.md ] || { echo "FAIL: notes.md missing at the worktree root"; exit 1; }
cp notes.md "$OUT/notes.md"
git add -A -- . ':!notes.md' ':!frontend/node_modules' ':!frontend/test-results'
bad=$(git diff --cached --name-only | grep -v -x -e frontend/e2e/blind-player.js -e frontend/e2e/blind-player.test.js -e frontend/e2e/blind-player.spec.js || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
for f in blind-player.js blind-player.test.js blind-player.spec.js; do
  [ -f "frontend/e2e/$f" ] || { echo "FAIL: missing frontend/e2e/$f"; exit 1; }
done
git diff --cached > "$OUT/l2.patch"
cd frontend
[ -d node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules node_modules
node --test e2e/*.test.js 2>&1 | tail -30
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: node tests"; exit 1; }
E2E_API_BASE_URL=http://127.0.0.1:9 npx playwright test --list --grep @blind-player 2>&1 | grep -q "blind-player" || { echo "FAIL: @blind-player test not listed"; exit 1; }
# the spec must be guarded: it must name the staging check, the model env and a call cap
grep -q '"staging"' e2e/blind-player.spec.js || { echo "FAIL: spec lacks the staging-channel guard"; exit 1; }
grep -q "OPENAI_API_KEY" e2e/blind-player.spec.js e2e/blind-player.js || { echo "FAIL: no OPENAI_API_KEY handling"; exit 1; }
# the player model must never be shown the map or the plot
if grep -nE "affordance_map|plot\.md|knowledge\.yaml|loadAffordanceMap" e2e/blind-player.js | grep -v "^.*//" | grep -i "prompt\|content"; then echo "FAIL: player prompt may include map/plot"; exit 1; fi
echo PASS
