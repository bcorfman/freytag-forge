#!/bin/bash
# Ringer check for the blind-player prompt recording fix (cwd = task worktree). Free: no network, no model.
set -u
OUT=/home/bcorfman/dev/ringer-work/affordance-l2-prompts
mkdir -p "$OUT"
[ -f notes.md ] || { echo "FAIL: notes.md missing at the worktree root"; exit 1; }
cp notes.md "$OUT/notes.md"
git add -A -- . ':!notes.md' ':!frontend/node_modules' ':!frontend/test-results'
allowed="-x -e frontend/e2e/blind-player.spec.js -e frontend/e2e/blind-player.js -e frontend/e2e/blind-player.test.js -e scripts/ringer/affordance/scene-affordance-l2-all-live.sh"
bad=$(git diff --cached --name-only | grep -v $allowed || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached --quiet && { echo "FAIL: no change was made"; exit 1; }
git diff --cached > "$OUT/prompts.patch"
cd frontend
[ -d node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules node_modules
node --test e2e/*.test.js 2>&1 | tail -30
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: node tests"; exit 1; }
E2E_API_BASE_URL=http://127.0.0.1:9 npx playwright test --list --grep @blind-player 2>&1 | grep -q "blind-player" || { echo "FAIL: @blind-player test not listed"; exit 1; }
# behaviour, run directly: an object prompt must be collected, and the old string-only filter must be gone
node --input-type=module -e '
import { collectPrompts, promptsCategory } from "./e2e/blind-player.js";
const p = { system: "S", user: "U" };
const got = collectPrompts([{ turn: 3, prompt: p }, { turn: 4, prompt: null }, { turn: 5, prompt: { system: "S" } }]);
if (got.length !== 1 || got[0].turn !== 3 || got[0].prompt.user !== "U") { console.error("FAIL: collectPrompts", JSON.stringify(got)); process.exit(1); }
if (promptsCategory("blind-player-r2") !== "blind-player-prompts-r2" || promptsCategory("blind-player") !== "blind-player-prompts") { console.error("FAIL: promptsCategory"); process.exit(1); }
' || exit 1
cd ..
grep -q 'typeof turn.prompt === "string"' frontend/e2e/blind-player.spec.js && { echo "FAIL: spec still filters prompts by string type"; exit 1; }
grep -q "collectPrompts" frontend/e2e/blind-player.spec.js || { echo "FAIL: spec does not use collectPrompts"; exit 1; }
grep -q "promptsCategory" frontend/e2e/blind-player.spec.js || { echo "FAIL: spec does not write the prompts file"; exit 1; }
grep -q "e2e-blind-player-prompts" scripts/ringer/affordance/scene-affordance-l2-all-live.sh || { echo "FAIL: wrapper does not clear old prompts files"; exit 1; }
bash -n scripts/ringer/affordance/scene-affordance-l2-all-live.sh || { echo "FAIL: wrapper syntax"; exit 1; }
echo PASS
