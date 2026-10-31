#!/usr/bin/env bash
# Round 1 check: new World/WorldSchema helpers exist with tests; storygame untouched; worldkeeper and focused suites pass.
set -euo pipefail
cd /home/bcorfman/dev/freytag-forge
PY=.venv/bin/python
export PYTHONPATH=$PWD TMPDIR=/tmp
NOTES=scripts/ringer/worldkeeper-boundary/round1-notes.md
if ! git diff --quiet -- storygame tests; then
  echo "FAIL: round 1 must not change storygame/ or tests/:"; git diff --stat -- storygame tests; exit 1
fi
test -f packages/worldkeeper/tests/test_boundary_helpers.py || { echo "FAIL: packages/worldkeeper/tests/test_boundary_helpers.py missing"; exit 1; }
$PY - "$NOTES" <<'PYEOF'
import sys
from pathlib import Path
from worldkeeper import World, WorldSchema
notes = Path(sys.argv[1]).read_text() if Path(sys.argv[1]).exists() else ""
core_world = ["descendants", "contains", "under_contents", "open_state", "is_item", "observable_items",
              "required_observations", "moved_since"]
core_schema = ["related_areas", "area_ancestors"]
optional_world = ["current_seat", "reachable_from_seat", "takeable_items", "fixed_visible_items",
                  "visible_vehicle_seats"]
tests = Path("packages/worldkeeper/tests/test_boundary_helpers.py").read_text()
errors = []
for name in core_world:
    if not callable(getattr(World, name, None)):
        errors.append(f"World.{name} missing")
for name in core_schema:
    if not callable(getattr(WorldSchema, name, None)):
        errors.append(f"WorldSchema.{name} missing")
for name in optional_world:
    if not callable(getattr(World, name, None)) and f"`{name}`" not in notes:
        errors.append(f"World.{name} missing and not explained in round1-notes.md as `{name}`")
for name in core_world + core_schema + [n for n in optional_world if callable(getattr(World, n, None))]:
    if f".{name}(" not in tests:
        errors.append(f"test_boundary_helpers.py never calls .{name}(")
src = Path("packages/worldkeeper/src/worldkeeper/model.py").read_text()
if "storygame" in src:
    errors.append("worldkeeper model.py mentions storygame; it must stay story-agnostic")
if errors:
    print("FAIL:\n" + "\n".join(errors)); sys.exit(1)
print("helpers present")
PYEOF
$PY -m pytest -q -p no:cacheprovider packages/worldkeeper/tests 2>&1 | tail -15
$PY -m pytest -q -p no:cacheprovider tests/test_world_model.py 2>&1 | tail -5
$PY -m ruff check packages/worldkeeper
$PY -m ruff format --check packages/worldkeeper
echo "PASS round 1"
