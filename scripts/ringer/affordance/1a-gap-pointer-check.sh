#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/1a-gap-pointer
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v \
  -e "^$D/\(knowledge\|storylet-routes\|world\)\.yaml$" -e "^$D/storylets\.md$" \
  -e '^tests/' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
test -f tests/test_1a_gap_pointer.py || { echo "FAIL: tests/test_1a_gap_pointer.py missing"; exit 1; }
n=$(grep -c "^def test_" tests/test_1a_gap_pointer.py)
[ "$n" -ge 6 ] || { echo "FAIL: need at least 6 test functions, has $n"; exit 1; }
uv run python -I - <<'PY' || exit 1
import subprocess, sys, yaml
D = "data/stories/continuity-initiative/"
new = yaml.safe_load(open(D + "knowledge.yaml"))
old = yaml.safe_load(subprocess.check_output(["git", "show", "HEAD:" + D + "knowledge.yaml"]).decode())
key = lambda d: d["knowledge"] if isinstance(d, dict) and "knowledge" in d else d
n = {k["id"]: k for k in key(new)}; o = {k["id"]: k for k in key(old)}
added = set(n) - set(o)
if added != {"k_sl_1a_f_r1", "k_sl_1a_f_r2"}:
    print("FAIL: expected exactly k_sl_1a_f_r1 and k_sl_1a_f_r2, got", sorted(added)); sys.exit(1)
want = {
 "k_sl_1a_f_r1": "The drawer slides out. It holds a stapler, spare batteries, pens, and binder clips. A thin gap beneath its lower edge is wide enough for Kristin's fingers.",
 "k_sl_1a_f_r2": "The initials are fresh, deep cuts. The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers.",
}
for k, text in want.items():
    r = n[k]
    if r["delivery_text"] != text:
        print("FAIL: delivery_text differs for", k, repr(r["delivery_text"])); sys.exit(1)
    if [e["fact_id"] for e in r["establishes"]] != ["drawer_gap_pointed_out"]:
        print("FAIL: establishes only drawer_gap_pointed_out for", k); sys.exit(1)
    if r["available_in_scenes"] != ["1A"]:
        print("FAIL: scenes for", k); sys.exit(1)
    if r["source"]["storylet_id"] != "SL-1A-F":
        print("FAIL: storylet id for", k); sys.exit(1)
for kid, r in o.items():
    if n[kid] != r:
        print("FAIL: existing reveal changed:", kid); sys.exit(1)
blob = open(D + "knowledge.yaml").read() + open(D + "storylet-routes.yaml").read() + open(D + "handoffs.yaml").read() + open(D + "pacing.yaml").read()
import re
for m in re.finditer(r"drawer_gap_pointed_out", blob):
    ctx = blob[max(0, m.start() - 160):m.start()]
    if re.search(r"(requires|conditions|equals|trigger|bridge)\s*:?[^\n]*\n?[^\n]*$", ctx) and "fact_id: drawer_gap_pointed_out\n    value" not in blob[m.start()-40:m.start()+60]:
        pass
print("structure ok")
PY
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
