#!/bin/bash
# Ringer check (cwd = task worktree): per-replicate L2 report + merge script.
set -u
OUT=/home/bcorfman/dev/ringer-work/affordance-parallel
mkdir -p "$OUT"
git add -A -- . ':!notes.md' ':!frontend/node_modules' ':!frontend/test-results'
bad=$(git diff --cached --name-only | grep -v -x -e frontend/e2e/blind-player.spec.js -e frontend/e2e/merge-blind-player.js -e frontend/e2e/merge-blind-player.test.js || true)
[ -z "$bad" ] || { echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -q merge-blind-player.js || { echo "FAIL: merge-blind-player.js missing"; exit 1; }
git diff --cached > "$OUT/a.patch"
cd frontend
[ -d node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules node_modules
node --test e2e/*.test.js 2>&1 | tail -30
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: node tests"; exit 1; }
E2E_API_BASE_URL=http://127.0.0.1:9 npx playwright test --list --grep @blind-player 2>&1 | grep -q blind-player || { echo "FAIL: not listed"; exit 1; }
for w in replicatePlan '"staging"' OPENAI_API_KEY; do grep -q "$w" e2e/blind-player.spec.js || { echo "FAIL: spec lacks $w"; exit 1; }; done
# end-to-end smoke of the merge CLI on two fixture reports, then a missing one
T=$(mktemp -d); mkdir -p "$T/artifacts"
for n in 1 2; do cat > "$T/artifacts/e2e-blind-player-r$n.json" <<JSON
{"story_id":"s","scene":"1A","replicates":[{"replicate":1,"scene":"1A","transition_fired":true,"transition_turn":$((7+n)),"turn_count":9,"commands":["Open the drawer."],"affordances":[{"entity_id":"drawer","deadline_met":true}],"stuck_runs":[],"silent_transition":false}],"aggregate":{}}
JSON
done
node e2e/merge-blind-player.js "$T/artifacts" 2 || { echo "FAIL: merge CLI on 2 fixtures"; exit 1; }
node -e 'const r=JSON.parse(require("fs").readFileSync(process.argv[1]));if(r.replicates.map(x=>x.replicate).join()!=="1,2"||r.aggregate.replicates!==2||r.aggregate.mean_transition_turn!==8.5){console.error("FAIL: merged shape",JSON.stringify(r.aggregate));process.exit(1)}' "$T/artifacts/e2e-blind-player.json" || exit 1
if node e2e/merge-blind-player.js "$T/artifacts" 3 2>"$T/err"; then echo "FAIL: merge accepted a missing replicate"; exit 1; fi
grep -q "r3" "$T/err" || { echo "FAIL: missing-replicate error does not name r3:"; cat "$T/err"; exit 1; }
echo PASS
