#!/usr/bin/env bash
# Check for the T9h opening condition v2 harness (free: no network, no model call).
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
ED=scripts/ringer/environment_narration
TOOL="$ED/opening_condition_v2.py"
TEST=tests/test_opening_condition_v2.py
ENFORCE="$ED/enforce_t9h_opening_v2.sh"
SCRATCH=/tmp/t9h-opening-v2-check
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

for f in "$TOOL" "$TEST" "$ENFORCE"; do [ -f "$f" ] || { echo "FAIL: missing $f" >&2; exit 1; }; done
"$PY" -m pytest -q -p no:cacheprovider --no-cov "$TEST" > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check "$TOOL" "$TEST" || exit 1
"$PY" -m ruff format --check "$TOOL" "$TEST" || exit 1
bash -n "$ENFORCE" || { echo "FAIL: enforce script does not parse" >&2; exit 1; }
for needle in "--max-calls 44" "--max-usd 0.057" "generate-2" "--max-calls 200" "--max-usd 0.02" "--min-interval-s 0.5" "local_worker.mjs"; do
  grep -qF -- "$needle" "$ENFORCE" || { echo "FAIL: enforce script lacks '$needle'" >&2; exit 1; }
done

"$PY" "$TOOL" --capture --out "$SCRATCH/capture.json" || { echo "FAIL: --capture" >&2; exit 1; }
"$PY" - "$SCRATCH/capture.json" <<'PY' || exit 1
import json
import sys

from storygame.story_package.loader import load_story_package
from worldkeeper import WorldSchema
from storygame.story_package.world_schema import world_source_schema_data

doc = json.load(open(sys.argv[1]))
package = load_story_package(__import__("pathlib").Path("data/stories/continuity-initiative"))
schema = WorldSchema.from_data(world_source_schema_data(package.world))
names = {item.id: item.name for item in package.world.items}
openings = sorted(item.id for item in package.world.items if schema.kind_is(item.kind, "opening"))
expected = {"back_door": ("1A", "Inspect the back door."), "house_gate": ("1A", "Inspect the house gate."),
            "service_gate": ("1B", "Inspect the service gate."), "facility_gate": ("2A", "Inspect the facility gate.")}
errors = []
if openings != sorted(["back_door", "house_gate", "service_gate", "facility_gate", "storm_drain"]):
    errors.append(f"package openings are {openings}; run the kind edit first")
things = {row.get("thing_id"): row for row in doc.get("things", [])}
if set(things) != set(expected):
    errors.append(f"capture things {sorted(things)} != {sorted(expected)} (storm_drain must be excluded)")
captured = 0
for thing_id, (scene, command) in expected.items():
    row = things.get(thing_id) or {}
    if row.get("scene_id") != scene or row.get("command") != command:
        errors.append(f"{thing_id}: scene/command {row.get('scene_id')}/{row.get('command')} != {scene}/{command}")
    if row.get("status") != "captured":
        print(f"note: {thing_id} status {row.get('status')}: {row.get('error')}")
        continue
    captured += 1
    request = row.get("request") or {}
    system, user = str(request.get("system", "")), str(request.get("user", ""))
    if not system.startswith("You are the narrator"):
        errors.append(f"{thing_id}: request is not the narrator request")
    if command not in user:
        errors.append(f"{thing_id}: narrator user prompt does not carry the command")
    if names[thing_id].lower() not in user.lower():
        errors.append(f"{thing_id}: narrator user prompt never names '{names[thing_id]}'")
    things_block = user[user.find("THINGS:"):user.find("CONSTRAINTS:")]
    if f"- {names[thing_id]}. Place:".lower() not in things_block.lower():
        errors.append(f"{thing_id}: THINGS does not list '- {names[thing_id]}. Place: ...' (live turns list the inspected thing); block was: {things_block!r}")
    if row.get("storylets_activated"):
        errors.append(f"{thing_id}: capture must not force-activate storylets, got {row.get('storylets_activated')}")
if captured < 3:
    errors.append(f"only {captured} things captured; the preregistration needs at least 3")
if errors:
    print("FAIL:\n  " + "\n  ".join(errors))
    sys.exit(1)
print(f"capture OK: {captured} of 4 things captured")
PY

"$PY" "$TOOL" --run --capture "$SCRATCH/capture.json" --samples 10 --max-calls 44 --max-usd 0.06 --confirm --out "$SCRATCH/rows.json" > "$SCRATCH/run.out" 2>&1
if [ $? -eq 0 ] || [ -e "$SCRATCH/rows.json" ]; then
  echo "FAIL: --run must refuse without CLOUDFLARE_WORKER_URL/TOKEN and write nothing" >&2; cat "$SCRATCH/run.out"; exit 1
fi
"$PY" "$TOOL" --run --capture "$SCRATCH/capture.json" --samples 10 --max-calls 39 --max-usd 0.06 --out "$SCRATCH/rows.json" > /dev/null 2>&1 && { echo "FAIL: --run accepted max-calls below the planned count or no --confirm" >&2; exit 1; }
echo PASS
