#!/usr/bin/env bash
# Ringer check: the canon harness must not require pacing events that carry a `when` condition.
set -euo pipefail
cd /home/bcorfman/dev/freytag-forge
(cd frontend && node --test src/*.test.js e2e/*.test.js) 2>&1 | tail -25
# the projection's conditional set must equal the events that have a `when` in the real pacing.yaml
want=$(.venv/bin/python -c "
import yaml
d=yaml.safe_load(open('data/stories/continuity-initiative/pacing.yaml'))
print(','.join(sorted(e['id'] for e in d['events'] if e.get('when'))))")
got=$(cd frontend && node --input-type=module -e "
import { loadPackagePacing } from './e2e/package-clock.js';
const p = loadPackagePacing({ storyId: 'continuity_initiative', repoRoot: '..' });
console.log(p.eventOrder.filter((id) => p.isConditional(id)).sort().join(','));")
if [ "$want" != "$got" ]; then echo "FAIL conditional set differs: pacing.yaml=[$want] projection=[$got]"; exit 1; fi
# the spec must not assert a conditional event fired, and must still assert unconditional ones
grep -q "isConditional" frontend/e2e/scene-runtime.spec.js || { echo "FAIL scene-runtime.spec.js never calls isConditional"; exit 1; }
grep -q "is missing pacing event" frontend/e2e/scene-runtime.spec.js || { echo "FAIL the unconditional missing-event assertion was removed"; exit 1; }
echo "conditional pacing events ok: $got"
