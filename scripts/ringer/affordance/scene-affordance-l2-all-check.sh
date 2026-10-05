#!/bin/bash
# Ringer check for the all-scenes L2 harness (cwd = task worktree). Free: no network, no model.
set -u
OUT=/home/bcorfman/dev/ringer-work/affordance-l2-all
mkdir -p "$OUT"
[ -f notes.md ] || { echo "FAIL: notes.md missing at the worktree root"; exit 1; }
cp notes.md "$OUT/notes.md"
git add -A -- . ':!notes.md' ':!frontend/node_modules' ':!frontend/test-results'
allowed="-x -e frontend/e2e/blind-player.spec.js -e frontend/e2e/blind-player.js -e frontend/e2e/blind-player.test.js -e frontend/e2e/merge-blind-player.js -e frontend/e2e/merge-blind-player.test.js -e scripts/ringer/affordance/digest.py -e tests/test_affordance_digest.py -e scripts/ringer/affordance/scene-affordance-l2-all-live.sh"
bad=$(git diff --cached --name-only | grep -v $allowed || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached --quiet && { echo "FAIL: no change was made"; exit 1; }
git diff --cached > "$OUT/all.patch"
cd frontend
[ -d node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules node_modules
node --test e2e/*.test.js 2>&1 | tail -30
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: node tests"; exit 1; }
E2E_API_BASE_URL=http://127.0.0.1:9 npx playwright test --list --grep @blind-player 2>&1 | grep -q "blind-player" || { echo "FAIL: @blind-player test not listed"; exit 1; }
cd ..
TMPDIR=/tmp uv run pytest -q tests/test_affordance_digest.py -p no:cacheprovider --no-cov 2>&1 | tail -15
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: digest tests"; exit 1; }
uv run ruff check scripts/ringer/affordance/digest.py tests/test_affordance_digest.py || { echo "FAIL: ruff"; exit 1; }
uv run ruff format --check scripts/ringer/affordance/digest.py tests/test_affordance_digest.py || { echo "FAIL: ruff format"; exit 1; }
f=frontend/e2e/blind-player.spec.js
for needle in E2E_BLIND_SCENES '"staging"' "turnLog" semantic_match; do
  grep -q "$needle" frontend/e2e/*.js scripts/ringer/affordance/digest.py || { echo "FAIL: $needle missing"; exit 1; }
done
grep -q "200" $f || { echo "FAIL: total model-call cap of 200 not in the spec"; exit 1; }
grep -q "60 \* 60_000\|60 \* 60000\|3_600_000\|3600000" $f || { echo "FAIL: 60 minute test timeout missing"; exit 1; }
[ -f scripts/ringer/affordance/scene-affordance-l2-all-live.sh ] || { echo "FAIL: wrapper script missing"; exit 1; }
bash -n scripts/ringer/affordance/scene-affordance-l2-all-live.sh || { echo "FAIL: wrapper syntax"; exit 1; }
# old single-scene path must be unchanged when E2E_BLIND_SCENE is a single id
grep -q "E2E_BLIND_SCENE" $f || { echo "FAIL: E2E_BLIND_SCENE lost"; exit 1; }
echo PASS
