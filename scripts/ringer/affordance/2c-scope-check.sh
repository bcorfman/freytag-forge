#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2c-scope
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
changed=$(git diff --cached -U0 $D/knowledge.yaml | grep '^[-+]' | grep -v '^[-+][-+]')
exp=$(printf -- '-  available_in_scenes: [2C, 3A]\n+  available_in_scenes: [2C]\n-  available_in_scenes: [2C, 3A]\n+  available_in_scenes: [2C]\n')
if [ "$(echo "$changed" | grep -c .)" != 4 ] || [ "$(echo "$changed" | grep -c -x -- '+  available_in_scenes: \[2C\]')" != 2 ] || [ "$(echo "$changed" | grep -c -x -- '-  available_in_scenes: \[2C, 3A\]')" != 2 ]; then
  echo "FAIL: knowledge.yaml diff is not exactly two [2C, 3A] -> [2C] edits:"; echo "$changed"; exit 1; fi
python3 - <<'PY' || exit 1
import re,sys
t=open("data/stories/continuity-initiative/knowledge.yaml").read()
for k in ("k_sl_2c_d_r1","k_sl_2c_d_r2"):
    blk=t.split("- id: "+k,1)[1].split("\n- id: ",1)[0]
    if "available_in_scenes: [2C]\n" not in blk: print("FAIL: wrong scope on",k); sys.exit(1)
PY
bad=$(git diff --cached --name-only | grep -v -e "^$D/knowledge.yaml$" -e '^tests/' -e '^bench/affordance_known_gaps.json$' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
