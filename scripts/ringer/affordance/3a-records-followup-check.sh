#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/3a-records-followup
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v \
  -e "^$D/\(knowledge\|storylet-routes\|world\|handoffs\)\.yaml$" -e "^$D/storylets\.md$" \
  -e '^tests/' -e '^bench/affordance_known_gaps.json$' \
  -e '^scripts/ringer/affordance/3a_records_corpus_diff.py$' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
test -f tests/test_3a_records_followup.py || { echo "FAIL: tests/test_3a_records_followup.py missing"; exit 1; }
n=$(grep -c "^def test_" tests/test_3a_records_followup.py)
[ "$n" -ge 6 ] || { echo "FAIL: need at least 6 test functions, has $n"; exit 1; }
uv run python -I - <<'PY' || exit 1
import subprocess, sys, yaml
D = "data/stories/continuity-initiative/"
new = yaml.safe_load(open(D + "knowledge.yaml"))
old = yaml.safe_load(subprocess.check_output(["git", "show", "HEAD:" + D + "knowledge.yaml"]).decode())
key = lambda d: d["knowledge"] if isinstance(d, dict) and "knowledge" in d else d
n = {k["id"]: k for k in key(new)}; o = {k["id"]: k for k in key(old)}
added = set(n) - set(o)
if len(added) != 1:
    print("FAIL: expected exactly one new reveal, got", sorted(added)); sys.exit(1)
r = n[added.pop()]
r1 = o["k_sl_3a_b_r1"]
for f in ("action_evidence", "earn_when", "delivery_text"):
    if r[f] != r1[f]:
        print("FAIL: new reveal differs from k_sl_3a_b_r1 in", f); sys.exit(1)
facts = [(e["fact_id"], e["value"]) for e in r["establishes"]]
if facts != [("conditioned_release_plan_known", True)]:
    print("FAIL: establishes must be only conditioned_release_plan_known, got", facts); sys.exit(1)
req = {(q["fact_id"], q.get("equals")) for q in r["requires"]}
want = {("michelle_reached", True), ("behavioral_experiments_known", True)}
if not want <= req:
    print("FAIL: requires missing", want - req); sys.exit(1)
if any(q["fact_id"] == "conditioned_release_plan_known" for q in r["requires"]):
    print("FAIL: the loader rejects a reveal that requires what it establishes; put the conditioned_release_plan_known == false guard in the storylet activation instead"); sys.exit(1)
rt = open(D + "storylet-routes.yaml").read()
sid = r["source"]["storylet_id"]
blk = rt.split("- id: " + sid + "\n")[1].split("\n- id: ")[0]
act = blk.split("realization_options")[0]
if "conditioned_release_plan_known" not in act or "equals: false" not in act:
    print("FAIL: storylet", sid, "activation must carry conditioned_release_plan_known equals false"); sys.exit(1)
if r["available_in_scenes"] != ["3A"]:
    print("FAIL: available_in_scenes must be [3A]"); sys.exit(1)
for kid in ("k_sl_3a_b_r2", "k_sl_3a_d_r1"):
    for f in ("action_evidence", "earn_when", "establishes", "delivery_text"):
        if n[kid][f] != o[kid][f]:
            print("FAIL:", kid, "changed in", f); sys.exit(1)
print("structure ok")
PY
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
