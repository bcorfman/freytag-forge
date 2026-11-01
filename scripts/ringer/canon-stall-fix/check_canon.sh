#!/usr/bin/env bash
# Ringer check: canon spec has no stall gate, requires only reached-due events, and ends on story_complete.
set -euo pipefail
cd /home/bcorfman/dev/freytag-forge
S=frontend/e2e/scene-runtime.spec.js
if grep -nE "MAX_STALLED_TURNS|stalledTurns|lastCommittedCount" "$S"; then echo "FAIL stall heuristic still in $S"; exit 1; fi
grep -q "canon-policy" "$S" || { echo "FAIL $S does not import canon-policy.js"; exit 1; }
grep -q "if (storyCompleteSeen) break;" "$S" || { echo "FAIL loop does not stop on storyCompleteSeen"; exit 1; }
if grep -q "scenePrompts\[sceneId\].length" "$S"; then echo "FAIL old prompt-count stop still present"; exit 1; fi
grep -qE "expect\(storyCompleteSeen" "$S" || { echo "FAIL no storyCompleteSeen assertion before judging"; exit 1; }
test -f frontend/e2e/canon-policy.js || { echo "FAIL canon-policy.js missing"; exit 1; }
test -f frontend/e2e/canon-policy.test.js || { echo "FAIL canon-policy.test.js missing"; exit 1; }
git diff --quiet HEAD -- frontend/e2e/package-clock.js data || { echo "FAIL edited a file outside ownership"; git diff --stat; exit 1; }
cd frontend
set -o pipefail
node --test src/*.test.js e2e/*.test.js 2>&1 | tail -25
