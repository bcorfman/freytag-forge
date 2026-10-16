#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
owned='^frontend/(src/clarification\.js|src/clarification\.test\.js|src/main\.js|e2e/blind-player\.js|e2e/blind-player\.spec\.js|e2e/blind-player\.test\.js)$'
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in frontend/src/clarification.js frontend/src/clarification.test.js frontend/src/main.js frontend/e2e/blind-player.js; do
  git diff --cached --name-only | grep -qx "$f" || { echo "missing deliverable $f"; exit 1; }
done
ln -sfn /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
git rm -q --cached frontend/node_modules 2>/dev/null
(cd frontend && npm test 2>&1 | tail -25; [ ${PIPESTATUS[0]} -eq 0 ]) || { echo "node tests failed"; exit 1; }
(cd frontend && VITE_API_BASE_URL=http://x npx vite build --outDir /tmp/stage4-front-dist --emptyOutDir 2>&1 | tail -5; [ ${PIPESTATUS[0]} -eq 0 ]) || { echo "vite build failed"; exit 1; }
git reset -q frontend/node_modules 2>/dev/null; git add -A -- . ':!frontend/node_modules' >/dev/null 2>&1
git diff --cached -- . ':!frontend/node_modules' > /home/bcorfman/dev/ringer-work/stage4-notes/reference-frontend.patch
grep -q 'node_modules' /home/bcorfman/dev/ringer-work/stage4-notes/reference-frontend.patch && { echo "patch contains node_modules"; exit 1; }
test -s /home/bcorfman/dev/ringer-work/stage4-notes/reference-frontend.patch || { echo "empty patch"; exit 1; }
