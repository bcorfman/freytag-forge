#!/usr/bin/env bash
# Ringer check for deleting SL-2C-D-R1 and SL-2C-D-R2. Runs in the task worktree.
set -euo pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
PY="$PWD/.venv/bin/python"
export PYTHONPATH="$PWD" TMPDIR=/tmp

echo "== 1. content check against HEAD =="
"$PY" - <<'PYEOF'
import subprocess, sys
from pathlib import Path
import yaml

path = "data/stories/continuity-initiative/storylet-routes.yaml"
head = yaml.safe_load(subprocess.check_output(["git", "show", f"HEAD:{path}"], text=True))
now = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

def storylets(doc):
    if isinstance(doc, dict):
        for v in doc.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "realization_options" in v[0]:
                return v
    if isinstance(doc, list):
        return doc
    raise SystemExit("cannot find storylet list")

h, n = storylets(head), storylets(now)
expected = []
for s in h:
    s = dict(s)
    if s["id"] == "SL-2C-D":
        ids = [r["id"] for r in s["realization_options"]]
        assert ids == ["SL-2C-D-R1", "SL-2C-D-R2", "SL-2C-D-R3", "SL-2C-D-R4"], f"HEAD SL-2C-D options changed: {ids}"
        s["realization_options"] = [r for r in s["realization_options"] if r["id"] not in ("SL-2C-D-R1", "SL-2C-D-R2")]
    expected.append(s)
if expected != n:
    for a, b in zip(expected, n):
        if a != b:
            print("FIRST DIFFERING STORYLET:", a["id"], "vs", b["id"])
            break
    else:
        print("storylet count differs:", len(expected), len(n))
    raise SystemExit("storylet-routes.yaml differs from HEAD in more than the removal of SL-2C-D-R1 and -R2")
print("ok: storylet-routes.yaml equals HEAD minus SL-2C-D-R1/-R2")
PYEOF

echo "== 2. no live reference left =="
if grep -rnE "SL-2C-D-R[12]\b" data tests/test_markdown_story_package.py storygame packages 2>/dev/null; then
  echo "FAIL: live references to SL-2C-D-R1/-R2 remain (listed above)"; exit 1
fi
echo "ok"

echo "== 3. only expected files changed =="
changed=$(git status --porcelain --untracked-files=all | sed -E 's/^.{3}//' | grep -vE '^\.venv$' | sort || true)
echo "$changed"
bad=$(echo "$changed" | grep -vE '^(data/stories/continuity-initiative/storylet-routes\.yaml|tests/[A-Za-z0-9_]+\.py)$' || true)
if [ -n "$bad" ]; then echo "FAIL: unexpected files changed:"; echo "$bad"; exit 1; fi

echo "== 4. focused tests =="
set -o pipefail
"$PY" -m pytest -q -p no:cacheprovider -x \
  tests/test_markdown_story_package.py tests/test_required_storylet_closure.py \
  tests/test_incident_loader.py tests/test_incident_engine.py tests/test_incident_recovery.py \
  tests/test_incident_characterization.py tests/test_branch_report.py tests/test_canon_journey.py \
  tests/test_phase1_slice_playthroughs.py tests/test_disclosure_matrix.py \
  tests/test_audit_budget.py tests/test_audit_budget_branches.py tests/test_prompt_budget.py \
  tests/test_recovery_budget.py tests/test_story_package_cache.py tests/test_loader_pacing_producers.py

echo "== 5. ruff =="
"$PY" -m ruff check tests storygame
"$PY" -m ruff format --check tests
echo "ALL CHECKS PASSED"
