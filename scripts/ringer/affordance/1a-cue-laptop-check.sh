#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/1a-cue-laptop
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/handoffs.yaml -e 'tests/.*\.py' || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
TMPDIR=/tmp uv run python - <<'P' || exit 1
import subprocess, yaml
from pathlib import Path
rd = lambda t: yaml.safe_load(t)["deliveries"]
base = {d["fact_id"]: d for d in rd(subprocess.check_output(["git", "show", "HEAD:data/stories/continuity-initiative/handoffs.yaml"], text=True))}
new = {d["fact_id"]: d for d in rd(Path("data/stories/continuity-initiative/handoffs.yaml").read_text())}
assert set(new) == set(base)
want = "Kristin's initials, KMS, are carved into a drawer of Michelle's workstation. The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
assert " ".join(new["continuity_initiative_known"]["cue_text"].split()) == want, new["continuity_initiative_known"]["cue_text"]
for k, v in new.items():
    if k == "continuity_initiative_known":
        assert {a: b for a, b in v.items() if a != "cue_text"} == {a: b for a, b in base[k].items() if a != "cue_text"}
    else:
        assert v == base[k], f"{k} changed"
print("data ok")
P
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
