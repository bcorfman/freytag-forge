#!/bin/bash
# Ringer check for the entry-knowledge fix. Runs in the task worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/entry-knowledge-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
git add -A -- data tests .plans
bad=$(git status --porcelain | grep -v -E '^[AM]  (data/stories/continuity-initiative/(knowledge.yaml|plot.md)|tests/.*|\.plans/disclosure-matrix\.(json|md))$' || true)
[ -z "$bad" ] || { echo "FAIL stray paths:"; echo "$bad"; exit 1; }
OUT=/home/bcorfman/dev/ringer-work/entry-knowledge-patches; mkdir -p $OUT
git diff --cached > $OUT/entry.patch
[ -s $OUT/entry.patch ] || { echo "FAIL empty patch"; exit 1; }
K=data/stories/continuity-initiative/knowledge.yaml
P=data/stories/continuity-initiative/plot.md
PYTHONPATH=$PWD $PY - <<'PY' || exit 1
import sys, yaml
from pathlib import Path
d = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text())
items = {k["id"]: k for k in d["knowledge"]}
def need(c, m):
    if not c:
        print("FAIL", m); sys.exit(1)
a = items["k_scene_2a_entry"]
need(a["statement"] == "Kristin must plan a way into the facility. False identities are a possible cover.", "2a statement")
need(a["aliases"] == ["false identities", "facility entrance"], "2a aliases")
c = items["k_scene_2c_entry"]
need(c["statement"] == "Kristin fears a possible purge. She must choose her next move.", "2c statement")
need(c["entity_ids"] == ["kristin", "purge_chamber"] and c["aliases"] == ["purge"], "2c entity_ids/aliases")
for i in ("k_sl_2c_b_r1", "k_sl_2c_b_r2"):
    need(items[i]["aliases"] == ["purge clock started", "purge clock"], i + " aliases")
fr = {f["scene_id"]: f["pressure"] for f in d["scene_frames"]}
need(fr["2B"] == "Find evidence in the records archive", "2B pressure")
need(fr["2C"] == "Choose the next move under growing pressure", "2C pressure")
need(fr["3B"] == "Reach the broadcast controls", "3B pressure")
txt = Path("data/stories/continuity-initiative/plot.md").read_text()
for old, new in (("Secure evidence while judging Brandons betrayal", "Find evidence in the records archive"),
                 ("Survive the purge clock and choose a combined mission", "Choose the next move under growing pressure"),
                 ("Overload JANUS with false alarms", "Reach the broadcast controls")):
    need(("objective: " + old) not in txt and ("objective: " + new) in txt, "plot objective " + new)
print("content ok")
PY
git diff --cached --stat -- $K $P | tail -3
# nothing but the intended lines may change in knowledge.yaml and plot.md
added=$(git diff --cached -U0 -- $K $P | grep -E '^[+-][^+-]' | wc -l)
[ "$added" -le 40 ] || { echo "FAIL too many changed lines in data: $added"; exit 1; }
PYTHONPATH=$PWD $PY -c "
from pathlib import Path
from storygame.story_package.loader import load_story_package
load_story_package(Path('data/stories/continuity-initiative')); print('package load ok')" || { echo "FAIL package load"; exit 1; }
PYTHONPATH=$PWD TMPDIR=/tmp $PY -m pytest -q -p no:cacheprovider -n auto 2>&1 | tail -15
[ ${PIPESTATUS[0]} -eq 0 ] || { echo "FAIL suite"; exit 1; }
$PY -m ruff check . && $PY -m ruff format --check . || exit 1
echo PASS
