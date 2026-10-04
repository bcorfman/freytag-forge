#!/bin/bash
# Ringer check for L1 (cwd = task worktree).
set -u
OUT=/home/bcorfman/dev/ringer-work/affordance-l1b
mkdir -p "$OUT"
[ -f notes.md ] || { echo "FAIL: notes.md missing at the worktree root"; exit 1; }
cp notes.md "$OUT/notes.md"
git add -A -- . ':!notes.md' ':!frontend/node_modules' ':!frontend/test-results'
bad=$(git diff --cached --name-only | grep -v -x -e frontend/e2e/affordances.js -e frontend/e2e/affordances.test.js  || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/l1b.patch"
cd frontend
[ -d node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules node_modules
node --test e2e/affordances.test.js e2e/scene-walk.test.js 2>&1 | tail -30
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: node tests"; exit 1; }
TMPDIR=/tmp node --input-type=module -e 'import {exploreInput} from "./e2e/affordances.js"; const r=exploreInput({location:{name:"Michelle\u0027s house"}}); if(r!=="Search Michelle\u0027s house."){console.error("FAIL got",r);process.exit(1)} if(exploreInput({location:{name:"freight terminal"}})!=="Search the freight terminal."){console.error("FAIL plain");process.exit(1)}'
# Free live read of the real package map through the module (no game, no network).
cd .. && TMPDIR=/tmp node --input-type=module -e '
import { loadAffordanceMap, firstStepAffordances } from "./frontend/e2e/affordances.js";
const m = loadAffordanceMap("data/stories/continuity-initiative");
const a = firstStepAffordances(m, "1A").map((x) => x.entity_id);
for (const want of ["michelle_drawer", "michelle_workstation"]) if (!a.includes(want)) { console.error("FAIL: 1A first-step affordances lack", want, "got", a); process.exit(1); }
console.log("1A first-step:", a.join(","));
' || exit 1
echo PASS
