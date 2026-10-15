#!/usr/bin/env bash
# runs in the task worktree
set -u
[ -e frontend/node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
git add -A -- . ':!frontend/node_modules' >/dev/null 2>&1
owned='^(frontend/e2e/(spine-record\.js|spine-record\.test\.js|spine-expected-reveals\.json|scene-runtime\.spec\.js)|tests/test_spine_expected_reveals\.py)$'
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in frontend/e2e/spine-record.js frontend/e2e/spine-record.test.js frontend/e2e/spine-expected-reveals.json tests/test_spine_expected_reveals.py; do
  git diff --cached --name-only | grep -qx "$f" || { echo "missing deliverable $f"; exit 1; }
done
(cd frontend && node --test e2e/spine-record.test.js e2e/canon-journey.test.js e2e/judge-journeys.test.js 2>&1 | tail -40; exit ${PIPESTATUS[0]}) || { echo "node tests failed"; exit 1; }
for f in frontend/e2e/spine-record.js frontend/e2e/scene-runtime.spec.js; do node --check "$f" 2>/dev/null || node --input-type=module --check < "$f" || { echo "syntax error in $f"; exit 1; }; done
PYTHONPATH=$PWD TMPDIR=/tmp /home/bcorfman/dev/freytag-forge/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider tests/test_spine_expected_reveals.py tests/test_canon_journey.py tests/test_2c_spine_prompts.py 2>&1 | tail -20; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
grep -q "story_complete" frontend/e2e/scene-runtime.spec.js || { echo "spine does not use story_complete"; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage3-notes/spine.patch
test -s /home/bcorfman/dev/ringer-work/stage3-notes/spine.patch || { echo "empty patch"; exit 1; }
