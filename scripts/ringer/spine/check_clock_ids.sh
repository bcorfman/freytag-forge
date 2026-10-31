#!/usr/bin/env bash
# Ringer check for the clock-ids task. Prints why it fails.
set -uo pipefail
R=/home/bcorfman/dev/freytag-forge
cd "$R/frontend"
out=$(node --test e2e/*.test.js src/*.test.js 2>&1); rc=$?
echo "$out" | grep -E "^# (pass|fail)"
if [ $rc -ne 0 ]; then echo "$out" | grep -A25 "failing tests" | head -40; echo "node tests fail"; exit 1; fi
if grep -n "pressure_1a" e2e/scene-runtime.spec.js e2e/package-clock.test.js; then echo "stale pressure_1a remains"; exit 1; fi
id=$(grep -oP 'fired_pacing_event_ids\).toContain\("\K[a-z0-9_]+' e2e/scene-runtime.spec.js)
echo "timed-events id=$id"
grep -q "^- id: ${id}$" "$R/data/stories/continuity-initiative/pacing.yaml" || { echo "$id is not a pacing.yaml event"; exit 1; }
echo "clock-ids ok"
