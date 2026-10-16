#!/usr/bin/env bash
set -u
[ -e frontend/node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
git add -A -- . ':!frontend/node_modules' >/dev/null 2>&1
owned='^frontend/e2e/(alias-smoke-record\.js|alias-smoke-record\.test\.js|scene-runtime\.spec\.js)$'
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in frontend/e2e/alias-smoke-record.js frontend/e2e/alias-smoke-record.test.js frontend/e2e/scene-runtime.spec.js; do
  git diff --cached --name-only | grep -qx "$f" || { echo "missing deliverable $f"; exit 1; }
done
(cd frontend && node --test e2e/alias-smoke-record.test.js e2e/spine-record.test.js e2e/knowledge-timeline-record.test.js 2>&1 | tail -20; exit ${PIPESTATUS[0]}) || { echo "node tests failed"; exit 1; }
node --input-type=module --check < frontend/e2e/scene-runtime.spec.js || { echo "syntax error in spec"; exit 1; }
git diff --cached -- frontend/e2e/scene-runtime.spec.js | grep -E '^-' | grep -vE '^---' > /tmp/alias-removed.txt
[ -s /tmp/alias-removed.txt ] && { echo "spec lines were removed/changed (only additions allowed):"; head /tmp/alias-removed.txt; exit 1; }
(set -a; E2E_API_BASE_URL=http://127.0.0.1:9 ; cd frontend && npx playwright test --list --grep @alias-smoke 2>&1 | grep -q "alias-smoke") || { echo "playwright does not list @alias-smoke"; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage3-notes/alias.patch
test -s /home/bcorfman/dev/ringer-work/stage3-notes/alias.patch || { echo "empty patch"; exit 1; }
