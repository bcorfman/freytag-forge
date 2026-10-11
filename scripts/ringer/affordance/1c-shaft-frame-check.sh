#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/1c-shaft-frame
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
git diff --cached > "$OUT/change.patch"
bad=$(git diff --cached --name-only | grep -v -e "^$D/knowledge\.yaml$" -e '^tests/' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
test -f notes.md || { echo "FAIL: notes.md missing"; exit 1; }
uv run python -I - <<'PY' || exit 1
import subprocess, sys, yaml
D = "data/stories/continuity-initiative/"
new = yaml.safe_load(open(D + "knowledge.yaml"))
old = yaml.safe_load(subprocess.check_output(["git", "show", "HEAD:" + D + "knowledge.yaml"]).decode())
frames = lambda d: {f["scene_id"]: f for f in d["scene_frames"]}
n, o = frames(new), frames(old)
want = o["1C"]["situation"] + " The observation shaft overlooks a processing line. Identification numbers are visible on the uniforms below."
if n["1C"]["situation"] != want:
    print("FAIL: 1C situation is", repr(n["1C"]["situation"])); sys.exit(1)
for k in o:
    if k != "1C" and n[k] != o[k]:
        print("FAIL: frame changed for", k); sys.exit(1)
if n["1C"]["pressure"] != o["1C"]["pressure"]:
    print("FAIL: 1C pressure changed"); sys.exit(1)
strip = lambda d: {k: v for k, v in d.items() if k != "scene_frames"}
if strip(new) != strip(old):
    print("FAIL: something other than scene_frames changed in knowledge.yaml"); sys.exit(1)
print("structure ok")
PY
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -30
exit ${PIPESTATUS[0]}
