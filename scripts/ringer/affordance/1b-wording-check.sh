#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/1b-wording
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/world.yaml -e $D/plot.md -e $D/handoffs.yaml -e $D/knowledge.yaml -e bench/affordance_known_gaps.json -e tests/test_markdown_story_package.py -e tests/test_canon_journey.py -e tests/test_cloudflare_transport.py -e tests/test_world_placements.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
TMPDIR=/tmp uv run python - <<'PY' || exit 1
import yaml
H = yaml.safe_load(open("data/stories/continuity-initiative/handoffs.yaml"))
for d in H["deliveries"]:
    if d["fact_id"] == "brandon_identified":
        assert "Brandon" not in d["cue_text"], "brandon_identified cue names Brandon"
    if d["fact_id"] == "missing_may_be_alive":
        assert "cue_text" not in d, "missing_may_be_alive cue not deleted"
PY
if grep -n "list of earlier disappearances" $D/handoffs.yaml; then echo "FAIL: missing_may_be_alive cue not deleted"; exit 1; fi
if grep -n "storm-drain entrance is open ahead" $D/handoffs.yaml; then echo "FAIL: park_pursuit cue still names the storm drain"; exit 1; fi
grep -q "id: service_gate" $D/world.yaml && grep -q "id: storm_drain" $D/world.yaml || { echo "FAIL: service_gate/storm_drain not declared in world.yaml"; exit 1; }
TMPDIR=/tmp uv run python /home/bcorfman/dev/freytag-forge/scripts/ringer/affordance/1b-wording-score.py || exit 1
TMPDIR=/tmp uv run python -m bench.affordance_map --help >/dev/null 2>&1 || true
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
