#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/3b-frame-d
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e data/stories/continuity-initiative/knowledge.yaml -e data/stories/continuity-initiative/plot.md -e 'tests/.*\.py' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
uv run python - <<'P' || exit 1
import re, sys, yaml
from pathlib import Path
D = Path("data/stories/continuity-initiative")
k = yaml.safe_load((D / "knowledge.yaml").read_text())
frame = next(f for f in k["scene_frames"] if f["scene_id"] == "3B")
ok = True
if frame["situation"] != "JANUS is tracking Kristin's moves.":
    print("FAIL: 3B situation is", repr(frame["situation"])); ok = False
if frame["pressure"] != "Feed JANUS false water and air alarms.":
    print("FAIL: 3B pressure is", repr(frame["pressure"])); ok = False
item = next(i for i in k["knowledge"] if i.get("id") == "k_scene_3b_entry")
blob = " ".join([item["statement"], *map(str, item.get("aliases") or []), *map(str, item.get("entity_ids") or [])])
if re.search(r"relay|broadcast", blob, re.I):
    print("FAIL: k_scene_3b_entry still names the relay or broadcast:", blob); ok = False
if item["establishes"] != [{"op": "assert", "fact_id": "scene_3b_entry_known", "value": True}]:
    print("FAIL: k_scene_3b_entry establishes changed"); ok = False
plot = (D / "plot.md").read_text()
beat = plot.split("### Scene 3B.1", 1)[1].split("###", 1)[0]
det = re.search(r"\*\*Details:\*\*\s*(.+)", beat).group(1)
if "relay" in det.lower():
    print("FAIL: 3B.1 Details still names the relay:", det); ok = False
if len([x for x in det.split(";") if x.strip()]) < 3:
    print("FAIL: 3B.1 Details has fewer than 3 items"); ok = False
sys.exit(0 if ok else 1)
P
d=$(git diff --cached -U0 -- data/stories/continuity-initiative | grep -E '^[+-][^+-]')
echo "$d"
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
