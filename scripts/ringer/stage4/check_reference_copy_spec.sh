#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev '^frontend/e2e/(reference-copy\.spec\.js|reference-copy\.js|reference-copy\.test\.js)$')
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in reference-copy.spec.js reference-copy.js reference-copy.test.js; do git diff --cached --name-only | grep -qx "frontend/e2e/$f" || { echo "missing $f"; exit 1; }; done
grep -q "@reference-copy" frontend/e2e/reference-copy.spec.js || { echo "tag missing"; exit 1; }
grep -q "requireStaging\|channel !== \"staging\"" frontend/e2e/reference-copy.spec.js || { echo "no staging guard"; exit 1; }
ln -sfn /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
(cd frontend && node --test e2e/reference-copy.test.js 2>&1 | tail -20; [ ${PIPESTATUS[0]} -eq 0 ]) || { echo "node tests failed"; exit 1; }
(cd frontend && node --check e2e/reference-copy.spec.js && node --check e2e/reference-copy.js) || { echo "syntax"; exit 1; }
(cd frontend && E2E_API_BASE_URL= npx playwright test --list --grep @reference-copy 2>&1 | tail -5)
git rm -q --cached frontend/node_modules 2>/dev/null; rm -f frontend/node_modules
git diff --cached > /home/bcorfman/dev/ringer-work/stage4-notes/reference-copy-spec.patch
test -s /home/bcorfman/dev/ringer-work/stage4-notes/reference-copy-spec.patch || { echo "empty patch"; exit 1; }
