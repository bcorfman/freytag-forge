#!/usr/bin/env bash
# Ringer check: the canon loop answers engine clarifications instead of asserting turn_index on them.
set -euo pipefail
cd /home/bcorfman/dev/freytag-forge
S=frontend/e2e/scene-runtime.spec.js
grep -q "answerClarifications\|resolveClarification" "$S" || { echo "FAIL spec does not use a clarification helper"; exit 1; }
grep -q "payload.clarification\|\.clarification" frontend/e2e/canon-policy.js || { echo "FAIL canon-policy.js has no clarification handling"; exit 1; }
grep -qE "clarification" frontend/e2e/canon-policy.test.js || { echo "FAIL no clarification tests"; exit 1; }
grep -q "expect(payload.state?.turn_index).toBe(turnIndex + 1)" "$S" || { echo "FAIL the turn_index assertion must stay (it now sees only the resolved turn)"; exit 1; }
git diff --quiet HEAD -- frontend/e2e/package-clock.js frontend/e2e/package-clock-controller.js frontend/e2e/helpers.js frontend/e2e/canon-journey.js frontend/src data storygame || { echo "FAIL edited a file outside ownership"; git diff --stat; exit 1; }
node --check "$S"
cd frontend
node --test src/*.test.js e2e/*.test.js 2>&1 | tail -25
