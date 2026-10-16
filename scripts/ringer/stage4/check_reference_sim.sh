#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Fvx scripts/ringer/stage4/reference_sim.py)
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -qx scripts/ringer/stage4/reference_sim.py || { echo "missing script"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
J=/home/bcorfman/.ringer/artifacts/deliverables/freytag-affordance-live-20261011T122828Z-p2193795/l2-all-x3/e2e-blind-player.json
mkdir -p /home/bcorfman/dev/ringer-work/stage4-notes
PYTHONPATH=$PWD $PY/python scripts/ringer/stage4/reference_sim.py "$J" > /home/bcorfman/dev/ringer-work/stage4-notes/reference-sim.md || { echo "script failed"; exit 1; }
for k in "commands measured" "asked" "unique" "evidence would change" "scenes with a collision"; do
  grep -qi "$k" /home/bcorfman/dev/ringer-work/stage4-notes/reference-sim.md || { echo "report lacks '$k'"; tail -20 /home/bcorfman/dev/ringer-work/stage4-notes/reference-sim.md; exit 1; }
done
$PY/ruff check scripts/ringer/stage4/reference_sim.py && $PY/ruff format --check scripts/ringer/stage4/reference_sim.py || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage4-notes/reference-sim.patch
