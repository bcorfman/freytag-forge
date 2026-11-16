#!/usr/bin/env bash
# Ringer check for dropping the unread_effect rule. Runs in the task worktree.
set -euo pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
PY="$PWD/.venv/bin/python"
export PYTHONPATH="$PWD" TMPDIR=/tmp

echo "== 1. rule is gone, the other five remain =="
"$PY" - <<'PYEOF'
import pytest
from pathlib import Path
from storygame.story_package import gap_rules
from storygame.story_package.gap_rules import RULES, run_gap_rules

expected = {"custody", "co_location", "no_strand", "single_reveal_strand", "no_producer"}
assert set(RULES) == expected, f"RULES is {sorted(RULES)}, expected {sorted(expected)}"
for name in ("_unread_effect_flags", "_run_unread_effect", "_scoped_sets"):
    assert not hasattr(gap_rules, name), f"{name} is still defined"
root = Path("data/stories/continuity-initiative")
with pytest.raises(ValueError, match="unknown rule"):
    run_gap_rules(root, "pursuit_1b", ["unread_effect"])
# no_producer still gives nothing on the real package, and the other rules still run.
from storygame.story_package.loader import load_story_package
package = load_story_package(root)
anchors = [e.id for e in package.pacing.events] + [i.id for i in package.incidents] + [t.id for t in package.pacing.transitions]
bad = [(a, f.subject) for a in anchors for f in run_gap_rules(root, a, ["no_producer"])]
assert not bad, f"no_producer results on the real package: {bad}"
flags = run_gap_rules(root, "officer_presses_1a")
rules = {f.rule for f in flags}
assert {"custody", "co_location", "no_strand"} <= rules, f"officer_presses_1a no longer flags the Reyes findings: {sorted(rules)}"
print("ok")
PYEOF

echo "== 2. no stray reference =="
hits=$(grep -rn "unread_effect" storygame tests scripts/gap_rules.py || true)
echo "$hits"
bad=$(echo "$hits" | grep -v "^$" | grep -vE '^tests/test_gap_rules\.py:' || true)
if [ -n "$bad" ]; then echo "FAIL: unread_effect still referenced outside the new test:"; echo "$bad"; exit 1; fi
n=$(echo "$hits" | grep -c "unread_effect" || true)
if [ "$n" -gt 2 ]; then echo "FAIL: $n references in tests/test_gap_rules.py (expected the one new test only)"; exit 1; fi

echo "== 3. only expected files changed =="
changed=$(git status --porcelain --untracked-files=all | sed -E 's/^.{3}//' | grep -vE '^\.venv$' | sort || true)
echo "$changed"
bad=$(echo "$changed" | grep -vE '^(storygame/story_package/gap_rules\.py|tests/test_gap_rules\.py)$' | grep -v '^$' || true)
if [ -n "$bad" ]; then echo "FAIL: unexpected files changed:"; echo "$bad"; exit 1; fi

echo "== 4. focused tests =="
set -o pipefail
"$PY" -m pytest -q -p no:cacheprovider -x tests/test_gap_rules.py tests/test_impact_report.py tests/test_branch_report.py tests/test_situation_trace.py

echo "== 5. ruff =="
"$PY" -m ruff check storygame tests
"$PY" -m ruff format --check storygame tests
echo "== 6. export patch outside the worktree =="
PATCH=/home/bcorfman/dev/ringer-work/drop-unread-effect.patch
git add storygame/story_package/gap_rules.py tests/test_gap_rules.py
git diff --cached HEAD > "$PATCH"
test -s "$PATCH" || { echo "FAIL: exported patch is empty"; exit 1; }
git diff --cached HEAD --stat
echo "patch written to $PATCH"
echo "ALL CHECKS PASSED"
