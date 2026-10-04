#!/bin/bash
# Ringer check (cwd = task worktree): parallel L2 wrapper script and manifest.
set -u
OUT=/home/bcorfman/dev/ringer-work/affordance-parallel
mkdir -p "$OUT"
git add -A -- . ':!notes.md' ':!frontend/node_modules' ':!frontend/test-results'
bad=$(git diff --cached --name-only | grep -v -x -e scripts/ringer/affordance/scene-affordance-l2-parallel-live.sh -e scripts/ringer/affordance/scene-affordance-l2-parallel-live.json || true)
[ -z "$bad" ] || { echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; }
git diff --cached > "$OUT/b.patch"
S=scripts/ringer/affordance/scene-affordance-l2-parallel-live.sh
bash -n "$S" || { echo "FAIL: bash -n"; exit 1; }
command -v shellcheck >/dev/null && { shellcheck -S warning "$S" || { echo "FAIL: shellcheck"; exit 1; }; }
for w in "variable set FREYTAG_RATE_LIMIT_PER_MINUTE" "variable delete FREYTAG_RATE_LIMIT_PER_MINUTE" "trap restore EXIT" E2E_BLIND_REPLICATE_INDEX "merge-blind-player.js" "digest.py" "--output" "wait "; do grep -q -- "$w" "$S" || { echo "FAIL: wrapper lacks: $w"; exit 1; }; done
# the cap must be raised exactly once and restored by the trap
[ "$(grep -c 'variable set' "$S")" -eq 1 ] || { echo "FAIL: cap raised more than once"; exit 1; }
python3 -c 'import json,sys;m=json.load(open("scripts/ringer/affordance/scene-affordance-l2-parallel-live.json"));t=m["tasks"];assert len(t)==1 and t[0]["check_timeout_s"]>=2400 and "l2-parallel-live.sh" in t[0]["check"],m' || { echo "FAIL: manifest shape"; exit 1; }
echo PASS
