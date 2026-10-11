#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-copy-step
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/knowledge.yaml -e $D/handoffs.yaml -e tests/test_candidate_matcher.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
TMPDIR=/tmp uv run python - <<'P' || exit 1
from pathlib import Path
from storygame.story_package.loader import load_story_package
import subprocess, yaml
base = yaml.safe_load(subprocess.check_output(["git", "show", "HEAD:data/stories/continuity-initiative/knowledge.yaml"], text=True))
base = {k["id"]: k for k in (base if isinstance(base, list) else base.get("knowledge", base.get("items", [])))}
new = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text())
new = {k["id"]: k for k in (new if isinstance(new, list) else new.get("knowledge", new.get("items", [])))}
EXPECT = ["read","check","search","study","open","inspect","review","secure","copy","finish copying","save","verify","back up","download","transfer","examine","analyze","eject","monitor","take","retrieve","get","grab","pick up","pull up","use","access","view","look at","load","plug in","bring up","show"]
c1 = new["k_sl_2c_c_r1"]; b1 = base["k_sl_2c_c_r1"]
assert list(c1["action_evidence"][0]) == EXPECT, f"c_r1 verbs wrong: {c1['action_evidence'][0]}"
assert c1["action_evidence"][1] == b1["action_evidence"][1], "c_r1 object group changed"
for k, v in new.items():
    if k == "k_sl_2c_c_r1":
        rest = {a: b for a, b in v.items() if a != "action_evidence"}
        brest = {a: b for a, b in base[k].items() if a != "action_evidence"}
        assert rest == brest, "c_r1 fields other than action_evidence changed"
    else:
        assert v == base[k], f"{k} changed"
assert set(new) == set(base)
h = yaml.safe_load(Path("data/stories/continuity-initiative/handoffs.yaml").read_text())
hs = h if isinstance(h, list) else next(v for v in h.values() if isinstance(v, list))
cue = next(x for x in hs if x.get("fact_id") == "evidence_ready_to_transmit")["cue_text"]
assert " ".join(cue.split()) == "The copied files are close at hand. Kristin can check the copied files. Sending them could expose her and Brandon.", cue
load_story_package(Path("data/stories/continuity-initiative"))
print("data ok")
P
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
