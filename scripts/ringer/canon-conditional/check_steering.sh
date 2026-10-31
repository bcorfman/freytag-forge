#!/usr/bin/env bash
# Ringer check: unfired conditional pacing events steer the canon clock only while strictly ahead.
set -euo pipefail
cd /home/bcorfman/dev/freytag-forge
bash scripts/ringer/canon-conditional/check_conditional.sh
grep -q "nextPendingEvent" frontend/e2e/scene-runtime.spec.js || { echo "FAIL scene-runtime.spec.js does not use nextPendingEvent"; exit 1; }
(cd frontend && node --input-type=module -e "
import { loadPackagePacing, nextPendingEvent } from './e2e/package-clock.js';
const p = loadPackagePacing({ storyId: 'continuity_initiative', repoRoot: '..' });
const none = new Set();
const at = (scene, turns, fired = none) => nextPendingEvent(p, scene, turns, fired)?.event_id;
const fail = (m) => { console.error('FAIL ' + m); process.exit(1); };
if (at('1A', 4) !== 'patrol_arrives_1a') fail('1A turn 4 should target patrol_arrives_1a, got ' + at('1A', 4));
if (at('1A', 4, new Set(['patrol_arrives_1a'])) === 'patrol_arrives_1a') fail('a fired event was returned');
for (const t of [5, 6]) if (at('1A', t) === 'officer_presses_1a' || at('1A', t) === 'patrol_enters_1a') fail('an unfired conditional event at its own turn steers the clock at 1A turn ' + t + ': ' + at('1A', t));
console.log('steering ok: 1A t5=' + at('1A', 5) + ' t6=' + at('1A', 6));
")
