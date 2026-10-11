#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/2a-supervisor-pointer
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/knowledge.yaml -e tests/test_candidate_matcher.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
TMPDIR=/tmp uv run python - <<'P' || exit 1
import subprocess, yaml
from pathlib import Path
base = {k["id"]: k for k in yaml.safe_load(subprocess.check_output(["git", "show", "HEAD:data/stories/continuity-initiative/knowledge.yaml"], text=True))["knowledge"]}
new = {k["id"]: k for k in yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text())["knowledge"]}
assert set(new) == set(base)
want = "Kristin and Brandon are at the facility perimeter. Their false identities pass the first security checks. A supervisor questions why their inspection was not scheduled. Kristin can explain the unscheduled inspection to the supervisor."
assert " ".join(new["k_sl_2a_e_r1"]["delivery_text"].split()) == want, new["k_sl_2a_e_r1"]["delivery_text"]
for k, v in new.items():
    if k == "k_sl_2a_e_r1":
        assert {a: b for a, b in v.items() if a != "delivery_text"} == {a: b for a, b in base[k].items() if a != "delivery_text"}, "other e_r1 fields changed"
    else:
        assert v == base[k], f"{k} changed"
print("data ok")
P
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
