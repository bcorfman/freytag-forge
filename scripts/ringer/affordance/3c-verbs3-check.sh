#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/3c-verbs3
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e "^$D/knowledge.yaml$" -e '^tests/' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
uv run python -I - <<'PY' || exit 1
import subprocess, sys, yaml
path = "data/stories/continuity-initiative/knowledge.yaml"
new = yaml.safe_load(open(path))
old = yaml.safe_load(subprocess.check_output(["git", "show", "HEAD:" + path]).decode())
key = lambda d: d["knowledge"] if isinstance(d, dict) and "knowledge" in d else d
n = {k["id"]: k for k in key(new)}; o = {k["id"]: k for k in key(old)}
add = {
 "k_sl_3c_d_r2": (0, {"answer the families", "reassure the families", "respond to the families"}),
 "k_sl_3c_e_r2": (1, {"Charles's last remote channel", "his last remote channel"}),
}
changed = set()
for key_, (grp, want) in add.items():
    kid = key_.split("#")[0]
    og = o[kid]["action_evidence"][grp]; ng = n[kid]["action_evidence"][grp]
    if [x for x in ng if x in og] != list(og) or len(set(ng) - set(og)) != len(ng) - len(og):
        print("FAIL: old words removed or reordered in", key_); sys.exit(1)
    if set(ng) - set(og) != want:
        print("FAIL: wrong additions for", key_, "got", sorted(set(ng) - set(og)), "want", sorted(want)); sys.exit(1)
    changed.add(kid)
for kid, item in o.items():
    a = dict(item); b = dict(n[kid])
    if kid in changed:
        a["action_evidence"] = b["action_evidence"] = None
        if o[kid]["action_evidence"][0 if kid != "k_sl_3c_b_r1" else 1] is None: pass
    if a != b:
        print("FAIL: unexpected change in", kid); sys.exit(1)
if set(n) != set(o): print("FAIL: entries added or removed"); sys.exit(1)
print("OK: only the four expected groups gained exactly the expected words")
PY
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
