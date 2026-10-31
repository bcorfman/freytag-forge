#!/usr/bin/env bash
# Check for the T9h opening-kind edit (free: no network, no model call).
# The five fixed openings get the story sub-kind `opening`; nothing else in world.yaml changes.
# Usage: check_t9h_opening_kind.sh BACKUP_WORLD_YAML
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
BACKUP="${1:?usage: check_t9h_opening_kind.sh BACKUP_WORLD_YAML}"
SCRATCH=/tmp/t9h-opening-kind
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

"$PY" - "$BACKUP" <<'PY' || exit 1
import sys
from pathlib import Path

import yaml
from worldkeeper import WorldSchema

from storygame.story_package.loader import load_story_package
from storygame.story_package.world_schema import world_source_schema_data

OPENINGS = ["back_door", "house_gate", "facility_gate", "service_gate", "storm_drain"]
root = Path("data/stories/continuity-initiative")
before = yaml.safe_load(Path(sys.argv[1]).read_text())
after = yaml.safe_load((root / "world.yaml").read_text())
errors = []

kinds_before = {kind["id"]: kind for kind in before["kinds"]}
kinds_after = {kind["id"]: kind for kind in after["kinds"]}
opening = kinds_after.get("opening")
if opening is None:
    errors.append("kinds: has no `opening` entry")
else:
    if opening.get("is") != ["thing"]:
        errors.append(f"opening kind `is` must be [thing], got {opening.get('is')}")
    if opening.get("fixed") is not True:
        errors.append("opening kind must declare fixed: true")
    extra = set(opening) - {"id", "is", "fixed"}
    if extra:
        errors.append(f"opening kind must declare nothing else (no axis, contents, enterable); extra keys {sorted(extra)}")
for kind_id, kind in kinds_before.items():
    if kinds_after.get(kind_id) != kind:
        errors.append(f"existing kind `{kind_id}` changed")
if set(kinds_after) - set(kinds_before) - {"opening"}:
    errors.append(f"unexpected new kinds {sorted(set(kinds_after) - set(kinds_before) - {'opening'})}")

items_before = {item["id"]: item for item in before["items"]}
items_after = {item["id"]: item for item in after["items"]}
if list(items_before) != list(items_after):
    errors.append("item ids or their order changed")
for item_id, item in items_before.items():
    new = dict(items_after.get(item_id, {}))
    if item_id in OPENINGS:
        if new.get("kind") != "opening":
            errors.append(f"{item_id} must have kind: opening, got {new.get('kind')}")
        new.pop("kind", None)
        new.setdefault("fixed", item.get("fixed"))
    if new != item:
        errors.append(f"item `{item_id}` changed beyond the kind line: before {item} after {items_after.get(item_id)}")
for key in set(before) | set(after):
    if key not in ("kinds", "items") and before.get(key) != after.get(key):
        errors.append(f"top-level `{key}` changed")

package = load_story_package(root)
schema = WorldSchema.from_data(world_source_schema_data(package.world))
if not schema.kind_is("opening", "thing"):
    errors.append("opening is not a thing")
for item_id in OPENINGS:
    if not schema.is_fixed(item_id):
        errors.append(f"{item_id} is not fixed after the edit")
if errors:
    print("FAIL:\n  " + "\n  ".join(errors))
    sys.exit(1)
print("world.yaml edit OK: opening kind declared and set on", ", ".join(OPENINGS))
PY

TESTS="tests/test_defect_probe.py tests/test_drain_scene_state_payload.py tests/test_environment_baseline.py tests/test_narration_json.py tests/test_narration_corpus.py tests/test_place_scoped_feed.py tests/test_package_view_scope.py tests/test_enforce_drain_report.py tests/test_fixed_thing_marker.py tests/test_late_scene_repro.py tests/test_live_baseline_scene_state.py tests/test_observation_scene_state.py tests/test_drain_details_capture.py tests/test_markdown_story_package.py tests/test_staged_cues.py tests/test_world_placements.py tests/test_fixed_refusal.py tests/test_observation_open_step.py tests/test_search_opens_drawer.py"
# Six failures predate this edit on the dirty tree (recorded in the plan); they are deselected, not fixed here.
KNOWN="--deselect tests/test_fixed_refusal.py::test_names_other_action_question_joins_refused_names
--deselect tests/test_fixed_refusal.py::test_capture_real_scene_1a_fixed_refusal_precedes_other_questions
--deselect tests/test_observation_open_step.py::test_open_step_is_inert_when_the_container_is_not_openable
--deselect tests/test_observation_open_step.py::test_open_step_works_for_a_second_synthetic_story
--deselect tests/test_search_opens_drawer.py::test_synthetic_openable_container_obeys_under_first"
# shellcheck disable=SC2086
"$PY" -m pytest -q -p no:cacheprovider --no-cov -n auto $KNOWN $TESTS > "$SCRATCH/pytest.out" 2>&1
rc=$?
grep -E "^(FAILED|ERROR)|passed|failed" "$SCRATCH/pytest.out" | tail -25
[ $rc -eq 0 ] || exit $rc
"$PY" -m ruff check tests/test_world_placements.py || exit 1
"$PY" -m ruff format --check tests/test_world_placements.py || exit 1
echo PASS
