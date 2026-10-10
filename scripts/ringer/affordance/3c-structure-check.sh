#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/3c-structure
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v \
  -e '^storygame/runtime/' -e "^$D/" -e '^tests/' -e '^bench/affordance_known_gaps.json$' \
  -e '^scripts/ringer/affordance/3c_cue_gate_probe.py$' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
n=$(grep -c "^def test_" tests/test_3c_cue_chain.py 2>/dev/null || echo 0)
[ "$n" -ge 7 ] || { echo "FAIL: tests/test_3c_cue_chain.py needs at least 7 test functions, has $n"; exit 1; }
cues=$(grep -c "cue_text" $D/handoffs.yaml)
# seven new 3C cue entries
c3=$(uv run python -I - <<'PY'
import yaml
d = yaml.safe_load(open("data/stories/continuity-initiative/handoffs.yaml"))["deliveries"]
print(sum(1 for x in d if x["scene_id"] == "3C" and x.get("cue_text")))
PY
)
[ "$c3" = 7 ] || { echo "FAIL: expected 7 scene-3C cue deliveries, found $c3"; exit 1; }
for s in "The gates at the surface remain shut." "Families of the missing are calling for word." "Reports from detention sites still reach the broadcast chamber."; do
  if grep -q "$s\"" $D/knowledge.yaml; then echo "FAIL: pointer still present: $s"; exit 1; fi
done
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
