#!/usr/bin/env bash
# Checks for T9h Step 3: `opening` as an engine base kind, and the opening condition check behind a flag.
# Usage: check_t9h_opening_wiring.sh kind|wiring
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
TASK="${1:?kind|wiring}"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN

run_tests() {  # CI view first, then local
  bash scripts/ringer/ci_sim_pytest.sh -n 8 "$@" > /tmp/opening-wiring-$TASK-sim.out 2>&1; rc=$?
  grep -E "^(FAILED|ERROR)|passed|failed|skipped" /tmp/opening-wiring-$TASK-sim.out | tail -20
  [ $rc -eq 0 ] || { echo "FAIL: tests fail in the CI simulation" >&2; exit 1; }
}

case "$TASK" in
  kind)
    "$PY" - <<'PY' || exit 1
import sys
from pathlib import Path

import yaml
from worldkeeper import BASE_KINDS, WorldSchema

from storygame.story_package.loader import load_story_package
from storygame.story_package.world_schema import world_source_schema_data

errors = []
if BASE_KINDS.get("opening") != ("thing",):
    errors.append(f"BASE_KINDS['opening'] must be ('thing',), got {BASE_KINDS.get('opening')!r}")
world = yaml.safe_load(Path("data/stories/continuity-initiative/world.yaml").read_text())
if any(kind.get("id") == "opening" for kind in world.get("kinds", [])):
    errors.append("world.yaml still declares a story kind `opening`")
openings = ["back_door", "house_gate", "facility_gate", "service_gate", "storm_drain"]
items = {item["id"]: item for item in world["items"]}
for item_id in openings:
    if items[item_id].get("kind") != "opening":
        errors.append(f"{item_id} lost kind: opening")
package = load_story_package(Path("data/stories/continuity-initiative"))
schema = WorldSchema.from_data(world_source_schema_data(package.world))
for item_id in openings:
    if not schema.is_fixed(item_id):
        errors.append(f"{item_id} not fixed")
# A story that never declares the kind can use it, and an opening is fixed by default.
try:
    synthetic = WorldSchema.from_data({"entities": [
        {"id": "yard", "kind": "area", "name": "yard"},
        {"id": "hatch", "kind": "opening", "name": "hatch"},
        {"id": "crate", "kind": "thing", "name": "crate"},
    ]})
except Exception as error:
    errors.append(f"a story without a kinds block cannot declare kind opening: {error}")
else:
    if not synthetic.kind_is("opening", "thing"):
        errors.append("opening is not a thing")
    if not synthetic.is_fixed("hatch"):
        errors.append("an undeclared-fixed opening is not fixed by default")
    if synthetic.is_fixed("crate"):
        errors.append("a plain thing became fixed")
guide = Path("docs/world-model-grounding.md").read_text()
if "`opening`" not in guide:
    errors.append("docs/world-model-grounding.md does not name the `opening` kind")
if errors:
    print("FAIL:\n  " + "\n  ".join(errors)); sys.exit(1)
print("kind OK")
PY
    run_tests packages/worldkeeper/tests tests/test_world_model.py tests/test_world_placements.py tests/test_package_view_scope.py tests/test_opening_condition_v2.py tests/test_markdown_story_package.py tests/test_place_scoped_feed.py tests/test_narration_json.py tests/test_environment_baseline.py
    "$PY" -m ruff check packages/worldkeeper && "$PY" -m ruff format --check packages/worldkeeper || exit 1
    ;;
  wiring)
    [ -f tests/test_opening_check.py ] || { echo "FAIL: tests/test_opening_check.py missing" >&2; exit 1; }
    grep -q "FREYTAG_OPENING_CHECK" storygame/web_demo.py || { echo "FAIL: web_demo has no FREYTAG_OPENING_CHECK flag" >&2; exit 1; }
    grep -q "_variant_b_question" tests/test_opening_check.py || { echo "FAIL: no byte-identity test against the probe's Variant B question" >&2; exit 1; }
    run_tests tests/test_opening_check.py tests/test_observation_verifier.py tests/test_observation_enforcement.py tests/test_observation_resume.py tests/test_observation_preview.py tests/test_observation_open_step.py tests/test_observation_scene_state.py tests/test_web_demo_observation_enforce.py tests/test_runtime_capture.py tests/test_jev_batching.py tests/test_fixed_refusal.py tests/test_search_opens_drawer.py tests/test_opening_condition_v2.py tests/test_drain_scene_state_payload.py
    "$PY" -m ruff check storygame tests/test_opening_check.py && "$PY" -m ruff format --check storygame tests/test_opening_check.py || exit 1
    ;;
  smoke-harness)
    S=scripts/ringer/environment_narration/enforce_t9h_opening_check.sh
    [ -f "$S" ] || { echo "FAIL: $S missing" >&2; exit 1; }
    bash -n "$S" || exit 1
    for needle in "--opening-check" "--enforce" "--scene-state" "observe_storm_drain_1b" "observe_service_gate_1b" "observe_back_door_1a" "--max-usd 0.06" "local_worker.mjs"; do
      grep -qF -- "$needle" "$S" || { echo "FAIL: $S lacks '$needle'" >&2; exit 1; }
    done
    "$PY" scripts/ringer/transcript_1a/live_baseline.py --route observe_service_gate_1b --replicates 1 --opening-check --out /tmp/ow-x --dry-run > /tmp/ow-noenforce.out 2>&1 && { echo "FAIL: --opening-check must require --enforce" >&2; exit 1; }
    for route in observe_service_gate_1b observe_back_door_1a observe_storm_drain_1b; do
      rm -rf /tmp/ow-dry-$route
      "$PY" scripts/ringer/transcript_1a/live_baseline.py --route $route --replicates 1 --enforce --scene-state --opening-check --dry-run --out /tmp/ow-dry-$route > /tmp/ow-dry-$route.out 2>&1 || { tail -20 /tmp/ow-dry-$route.out; echo "FAIL: dry run $route" >&2; exit 1; }
    done
    run_tests tests/test_live_baseline_enforce.py tests/test_live_baseline_scene_state.py tests/test_live_baseline_opening_check.py tests/test_live_baseline_scene_start.py
    "$PY" -m ruff check scripts/ringer/transcript_1a/live_baseline.py tests/test_live_baseline_opening_check.py && "$PY" -m ruff format --check scripts/ringer/transcript_1a/live_baseline.py tests/test_live_baseline_opening_check.py || exit 1
    ;;
  retry-fact)
    [ -f tests/test_opening_retry_fact.py ] || { echo "FAIL: tests/test_opening_retry_fact.py missing" >&2; exit 1; }
    for f in FREYTAG_OPENING_RETRY_FACT FREYTAG_OPENING_THINGS_FACT; do grep -q "$f" storygame/web_demo.py || { echo "FAIL: web_demo lacks $f" >&2; exit 1; }; done
    run_tests tests/test_opening_retry_fact.py tests/test_opening_check.py tests/test_observation_enforcement.py tests/test_observation_resume.py tests/test_web_demo_observation_enforce.py tests/test_runtime_capture.py tests/test_narration_json.py tests/test_observation_preview.py
    "$PY" -m ruff check storygame tests/test_opening_retry_fact.py && "$PY" -m ruff format --check storygame tests/test_opening_retry_fact.py || exit 1
    ;;
  things-fact)
    [ -f tests/test_opening_things_fact.py ] || { echo "FAIL: tests/test_opening_things_fact.py missing" >&2; exit 1; }
    run_tests tests/test_opening_things_fact.py tests/test_place_scoped_feed.py tests/test_package_view_scope.py tests/test_narration_json.py tests/test_environment_baseline.py tests/test_drain_scene_state_payload.py tests/test_scene_1b_grounding.py tests/test_opening_condition_v2.py
    "$PY" -m ruff check storygame tests/test_opening_things_fact.py && "$PY" -m ruff format --check storygame tests/test_opening_things_fact.py || exit 1
    ;;
  arms-harness)
    S=scripts/ringer/environment_narration/enforce_t9h_opening_check.sh
    bash -n "$S" || exit 1
    for needle in "retry)" "things)" "--opening-retry-fact" "--opening-things-fact" "--replicates 5" "--max-usd 0.06"; do
      grep -qF -- "$needle" "$S" || { echo "FAIL: $S lacks '$needle'" >&2; exit 1; }
    done
    for flag in --opening-retry-fact --opening-things-fact; do
      rm -rf /tmp/ow-arm$flag
      "$PY" scripts/ringer/transcript_1a/live_baseline.py --route observe_service_gate_1b --replicates 1 --enforce --scene-state --opening-check $flag --dry-run --out /tmp/ow-arm$flag > /tmp/ow-arm$flag.out 2>&1 || { tail -20 /tmp/ow-arm$flag.out; echo "FAIL: dry run with $flag" >&2; exit 1; }
    done
    run_tests tests/test_live_baseline_opening_check.py tests/test_live_baseline_enforce.py tests/test_live_baseline_scene_state.py
    "$PY" -m ruff check scripts/ringer/transcript_1a/live_baseline.py && "$PY" -m ruff format --check scripts/ringer/transcript_1a/live_baseline.py || exit 1
    ;;
  *) echo "usage: check_t9h_opening_wiring.sh kind|wiring|smoke-harness|retry-fact|things-fact|arms-harness" >&2; exit 2 ;;
esac
echo PASS
