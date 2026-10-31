#!/usr/bin/env bash
# Round 3 check: no fallback walk in taking.py, test_taking uses the real World, reachable_from_seat returns ids.
set -euo pipefail
cd /home/bcorfman/dev/freytag-forge
PY=.venv/bin/python
export PYTHONPATH=$PWD TMPDIR=/tmp
fail() { echo "FAIL: $*"; exit 1; }
grep -q "hasattr(world" storygame/runtime/taking.py && fail "taking.py still has the hasattr fallback"
grep -qE "schema\.is_fixed|world\.area\(" storygame/runtime/taking.py && fail "taking.py still walks the world itself"
grep -q "^class World" tests/test_taking.py && fail "tests/test_taking.py still defines a fake World"
grep -qE "from worldkeeper import|import worldkeeper" tests/test_taking.py || fail "tests/test_taking.py does not use worldkeeper"
before=$(git show HEAD:tests/test_taking.py | grep -c "^def test_")
after=$(grep -c "^def test_" tests/test_taking.py)
[ "$after" -ge "$before" ] || fail "test_taking.py lost tests ($before -> $after)"
grep -qi "legacy" packages/worldkeeper/src/worldkeeper/model.py && fail "model.py still mentions legacy"
$PY - <<'PYEOF'
import inspect
from worldkeeper import World
src = inspect.getsource(World.reachable_from_seat)
assert "self.name(" not in src, "World.reachable_from_seat must return ids, not names"
print("reachable_from_seat returns ids")
PYEOF
grep -q "reachable_from_seat" storygame/runtime/seating.py || fail "seating.py no longer calls reachable_from_seat"
T=$(grep -rlE --include="*.py" "runtime\.(item_facts|capture|observation|seating|taking|fixed_refusal|traversal|narration_safety)\b|runtime import .*\b(item_facts|capture|observation|seating|taking|fixed_refusal|traversal|narration_safety)\b" tests | sort | tr '\n' ' ')
$PY -m pytest -q -p no:cacheprovider -n 8 $T packages/worldkeeper/tests 2>&1 | tail -15
$PY -m ruff check storygame packages tests/test_taking.py
$PY -m ruff format --check storygame packages tests/test_taking.py
echo "PASS round 3"
