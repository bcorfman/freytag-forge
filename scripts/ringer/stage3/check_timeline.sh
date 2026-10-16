#!/usr/bin/env bash
set -u
[ -e frontend/node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules
git add -A -- . ':!frontend/node_modules' >/dev/null 2>&1
owned='^(deployment/knowledge-timeline-script\.json|frontend/e2e/(scene-runtime\.spec\.js|knowledge-timeline-record\.js|knowledge-timeline-record\.test\.js)|tests/test_knowledge_timeline_script\.py)$'
bad=$(git diff --cached --name-only | grep -Ev "$owned")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in deployment/knowledge-timeline-script.json tests/test_knowledge_timeline_script.py frontend/e2e/scene-runtime.spec.js; do
  git diff --cached --name-only | grep -qx "$f" || { echo "missing deliverable $f"; exit 1; }
done
(cd frontend && node --test e2e/knowledge-timeline-record.test.js e2e/spine-record.test.js 2>&1 | tail -20; exit ${PIPESTATUS[0]}) || { echo "node tests failed"; exit 1; }
node --input-type=module --check < frontend/e2e/scene-runtime.spec.js || { echo "syntax error in spec"; exit 1; }
PYTHONPATH=$PWD TMPDIR=/tmp /home/bcorfman/dev/freytag-forge/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider tests/test_knowledge_timeline_script.py 2>&1 | tail -20; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
/home/bcorfman/dev/freytag-forge/.venv/bin/ruff check tests/test_knowledge_timeline_script.py && /home/bcorfman/dev/freytag-forge/.venv/bin/ruff format --check tests/test_knowledge_timeline_script.py || { echo ruff; exit 1; }
git diff --cached -- frontend/e2e/scene-runtime.spec.js | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' > /tmp/timeline-spec-diff.txt
grep -qE 'drives the main spine|llm-canon' /tmp/timeline-spec-diff.txt && { echo "diff touches another test"; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage3-notes/timeline.patch
test -s /home/bcorfman/dev/ringer-work/stage3-notes/timeline.patch || { echo "empty patch"; exit 1; }
