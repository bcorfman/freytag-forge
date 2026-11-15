#!/usr/bin/env bash
# Ringer check for renaming "flag" to "rule result". Runs in the task worktree.
set -euo pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
PY="$PWD/.venv/bin/python"
export PYTHONPATH="$PWD" TMPDIR=/tmp
FILES="storygame/story_package/gap_rules.py scripts/gap_rules.py tests/test_gap_rules.py docs/story-gap-guide.md"

echo "== 1. the word flag is gone from the owned files =="
if grep -n -i flag $FILES; then echo "FAIL: 'flag' still appears (listed above)"; exit 1; fi
echo ok

echo "== 2. new names exist, old names do not, report text changed as specified =="
"$PY" - <<'PYEOF'
from pathlib import Path
from storygame.story_package import gap_rules
assert hasattr(gap_rules, "RuleResult") and hasattr(gap_rules, "render_rule_results")
assert not hasattr(gap_rules, "Flag") and not hasattr(gap_rules, "render_flags")
text = gap_rules.render_rule_results([], "officer_presses_1a")
assert text.startswith("# Gap rule results: officer_presses_1a"), text[:80]
assert "No rule results." in text, text
assert "Rule results are reported, never block a build, and are not judgments; read the evidence." in text, text
results = gap_rules.run_gap_rules(Path("data/stories/continuity-initiative"), "officer_presses_1a")
assert {r.rule for r in results} >= {"custody", "co_location", "no_strand"}, sorted({r.rule for r in results})
assert all(type(r).__name__ == "RuleResult" for r in results)
print("ok")
PYEOF
out=$("$PY" scripts/gap_rules.py officer_presses_1a)
echo "$out" | head -3
echo "$out" | grep -q "^# Gap rule results: officer_presses_1a" || { echo "FAIL: script header wrong"; exit 1; }

echo "== 3. only expected files changed =="
changed=$(git status --porcelain --untracked-files=all | sed -E 's/^.{3}//' | grep -vE '^\.venv$' | sort || true)
echo "$changed"
bad=$(echo "$changed" | grep -vE '^(storygame/story_package/gap_rules\.py|scripts/gap_rules\.py|tests/test_gap_rules\.py|docs/story-gap-guide\.md)$' | grep -v '^$' || true)
if [ -n "$bad" ]; then echo "FAIL: unexpected files changed:"; echo "$bad"; exit 1; fi

echo "== 4. focused tests =="
set -o pipefail
"$PY" -m pytest -q -p no:cacheprovider -x tests/test_gap_rules.py tests/test_situation_trace.py tests/test_branch_report.py tests/test_impact_report.py

echo "== 5. ruff =="
"$PY" -m ruff check storygame tests scripts/gap_rules.py
"$PY" -m ruff format --check storygame tests scripts/gap_rules.py

echo "== 6. export patch outside the worktree =="
PATCH=/home/bcorfman/dev/ringer-work/rename-flag-to-rule-result.patch
git add $FILES
git diff --cached HEAD > "$PATCH"
test -s "$PATCH" || { echo "FAIL: exported patch is empty"; exit 1; }
git diff --cached HEAD --stat
echo "patch written to $PATCH"
echo "ALL CHECKS PASSED"
