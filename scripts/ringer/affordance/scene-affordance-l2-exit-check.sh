#!/bin/bash
# Ringer check for the L2 per-turn report + digest (cwd = task worktree). Pass "js" or "digest".
set -u
WHICH="$1"
OUT=/home/bcorfman/dev/ringer-work/affordance-l2-exit
mkdir -p "$OUT"
[ -f notes.md ] || { echo "FAIL: notes.md missing at the worktree root"; exit 1; }
cp notes.md "$OUT/notes-$WHICH.md"
git add -A -- . ':!notes.md' ':!frontend/node_modules' ':!frontend/test-results'
if [ "$WHICH" = js ]; then
  allowed="-x -e frontend/e2e/blind-player.js -e frontend/e2e/blind-player.test.js -e scripts/ringer/affordance/digest.py -e tests/test_affordance_digest.py"
else
  allowed="-x -e scripts/ringer/affordance/digest.py -e tests/test_affordance_digest.py"
fi
bad=$(git diff --cached --name-only | grep -v $allowed || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached --quiet && { echo "FAIL: no change was made"; exit 1; }
git diff --cached > "$OUT/$WHICH.patch"
if [ "$WHICH" = js ]; then
  cd frontend
  [ -d node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules node_modules
  node --test e2e/*.test.js 2>&1 | tail -30
  [ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: node tests"; exit 1; }
  E2E_API_BASE_URL=http://127.0.0.1:9 npx playwright test --list --grep @blind-player 2>&1 | grep -q "blind-player" || { echo "FAIL: @blind-player test not listed"; exit 1; }
  grep -q "exit_cause" e2e/blind-player.js || { echo "FAIL: exit_cause missing"; exit 1; }
  TMPDIR=/tmp uv run pytest -q ../tests/test_affordance_digest.py -p no:cacheprovider --no-cov 2>&1 | tail -15
  [ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: digest tests"; exit 1; }
  grep -q "turnLog" e2e/blind-player.spec.js || { echo "FAIL: spec does not use turnLog"; exit 1; }
  grep -q "transcript: transcripts" e2e/blind-player.spec.js && { echo "FAIL: spec still writes the cumulative transcript array"; exit 1; }
  grep -q "semantic_match" e2e/blind-player.js || { echo "FAIL: semantic_match recording lost"; exit 1; }
  grep -q '"staging"' e2e/blind-player.spec.js || { echo "FAIL: staging guard lost"; exit 1; }
else
  TMPDIR=/tmp uv run pytest -q tests/test_affordance_digest.py -p no:cacheprovider --no-cov 2>&1 | tail -15
  [ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: digest tests"; exit 1; }
  # the real, old-format report must still print (free, no network)
  for f in /home/bcorfman/dev/freytag-forge/artifacts/e2e-blind-player.json /home/bcorfman/dev/freytag-forge/artifacts/e2e-affordances.json; do
    [ -f "$f" ] && { uv run python scripts/ringer/affordance/digest.py "$f" > /dev/null || { echo "FAIL: digest crashed on $f"; exit 1; }; }
  done
fi
echo PASS
