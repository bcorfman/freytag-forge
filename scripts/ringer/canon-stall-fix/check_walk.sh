#!/usr/bin/env bash
# Ringer check: scene walker has no stall gate and shares nextPendingEvent.
set -euo pipefail
cd /home/bcorfman/dev/freytag-forge
W=frontend/e2e/scene-walk.js
if grep -nE "MAX_STALLED_TURNS|stalled|committedNow" "$W"; then echo "FAIL stall heuristic still in $W"; exit 1; fi
grep -q 'import { nextPendingEvent } from "./package-clock.js";' "$W" || { echo "FAIL nextPendingEvent not imported"; exit 1; }
grep -q "nextPendingEvent(pacing, sceneId, turns, fired)" "$W" || { echo "FAIL milestoneFor does not call nextPendingEvent"; exit 1; }
git diff --quiet HEAD -- frontend/e2e/package-clock.js data || { echo "FAIL edited a file outside ownership"; git diff --stat; exit 1; }
cd frontend
set -o pipefail
node --test e2e/scene-walk.test.js 2>&1 | tail -25
