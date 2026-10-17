#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
OWN='^frontend/e2e/(scene-runtime\.spec\.js|knowledge-timeline-record\.js|knowledge-timeline-record\.test\.js)$'
bad=$(git diff --cached --name-only | grep -Ev "$OWN")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -qx "frontend/e2e/scene-runtime.spec.js" || { echo "scene-runtime.spec.js not changed"; exit 1; }
grep -q "isFixedRefusalLine" frontend/e2e/scene-runtime.spec.js || { echo "spec does not use isFixedRefusalLine"; exit 1; }
grep -q "visibleLine !== " frontend/e2e/scene-runtime.spec.js && { echo "old inequality still present"; exit 1; }
node --check frontend/e2e/scene-runtime.spec.js || exit 1
(cd frontend && node --test e2e/knowledge-timeline-record.test.js 2>&1 | tail -15; exit ${PIPESTATUS[0]}) || { echo "node tests failed"; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage5-notes/refusal-e2e-line.patch
test -s /home/bcorfman/dev/ringer-work/stage5-notes/refusal-e2e-line.patch || { echo "empty patch"; exit 1; }
