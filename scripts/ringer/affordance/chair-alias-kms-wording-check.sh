#!/bin/bash
# Ringer check: run in the task worktree (cwd). Exports patch, verifies exact edits, runs suite.
set -u
OUT=/home/bcorfman/dev/ringer-work/chair-alias-kms-wording
mkdir -p "$OUT"
D=data/stories/continuity-initiative
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e $D/world.yaml -e $D/plot.md -e $D/handoffs.yaml -e $D/knowledge.yaml -e bench/affordance_known_gaps.json -e tests/test_markdown_story_package.py -e tests/test_bench_item_facts.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
for f in world.yaml plot.md handoffs.yaml knowledge.yaml; do
  n=$(git diff --cached --numstat -- $D/$f | awk '{print $1" "$2}')
  echo "$f added/removed: $n"
done
want() { # file added removed
  got=$(git diff --cached --numstat -- $D/$1 | awk '{print $1" "$2}')
  [ "$got" = "$2 $3" ] || { echo "FAIL: $1 changed '$got' lines (added removed), expected '$2 $3'"; exit 1; }
}
want world.yaml 1 0
want plot.md 2 2
want handoffs.yaml 1 1
want knowledge.yaml 2 2
grep -q "def test_1a_deadline_fallback_names_the_drawer" tests/test_markdown_story_package.py || { echo "FAIL: fallback test not renamed"; exit 1; }
if grep -n 'assert "KMS" in' tests/test_markdown_story_package.py; then echo "FAIL: KMS pin still in test"; exit 1; fi
if git diff --cached -U0 -- tests/test_bench_item_facts.py | grep '^+' | grep -q "def test_\|aliases"; then echo "FAIL: only the one test body may change"; exit 1; fi
git show HEAD:bench/affordance_known_gaps.json > "$OUT/gaps_before.json"
TMPDIR=/tmp uv run python - "$OUT/gaps_before.json" <<'PY' || exit 1
import json,sys
old=json.load(open(sys.argv[1])); new=json.load(open("bench/affordance_known_gaps.json"))
keep=[x for x in old if not (x.get("scene_id")=="1A" and x.get("subject")=="workstation_chair")]
assert len(old)-len(keep)==3, f"expected 3 chair entries in the old list, found {len(old)-len(keep)}"
assert new==keep, "known-gaps file must equal the old list minus the three 1A workstation_chair entries, same order"
print("known gaps ok:", len(new), "left")
PY
grep -n -A2 "id: workstation_chair" $D/world.yaml | grep -q "aliases: \[chair\]" || { echo "FAIL: workstation_chair lacks 'aliases: [chair]' right after its name"; exit 1; }
for f in plot.md handoffs.yaml; do
  if grep -n "carved with \(her\|Kristin's\) initials" $D/$f; then echo "FAIL: leftover 'carved with ... initials' wording in $f"; exit 1; fi
done
if grep -n "taped beneath the KMS drawer\|KMS drawer and takes" $D/knowledge.yaml; then echo "FAIL: statement or delivery_text still says 'KMS drawer'"; exit 1; fi
git diff --cached -U0 -- $D/plot.md $D/handoffs.yaml $D/knowledge.yaml | grep '^[+-][^+-]' 
TMPDIR=/tmp uv run python -m bench.affordance_map --package $D --out "$OUT/ci.json" || { echo "FAIL: L0 CLI"; exit 1; }
TMPDIR=/tmp uv run pytest -q -p no:cacheprovider 2>&1 | tail -40
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: pytest"; exit 1; }
echo PASS
