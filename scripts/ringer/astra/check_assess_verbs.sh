#!/usr/bin/env bash
# Check for astra-2c-assess-verbs: scope, patch export, tests, ruff. Runs inside the Ringer worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-2c-assess-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
git add -A -- data tests
bad=$(git status --porcelain | grep -v -E '^(A|M)  (data/stories/continuity-initiative/knowledge\.yaml|tests/test_2c_assess_verbs\.py)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
OUT=/home/bcorfman/dev/ringer-work/astra-patches; mkdir -p "$OUT"
git diff --cached > "$OUT/assess.patch"
[ -s "$OUT/assess.patch" ] || { echo "FAIL empty patch"; exit 1; }
# Only action_evidence lines may change in knowledge.yaml.
changed=$(git diff --cached -U0 -- data/stories/continuity-initiative/knowledge.yaml | grep -E '^[+-][^+-]' | grep -v -E '^[+-]\s*- \[' || true)
[ -z "$changed" ] || { echo "FAIL knowledge.yaml changes outside action_evidence verb/noun lists:"; echo "$changed"; exit 1; }
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not imported from worktree"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov tests/test_2c_assess_verbs.py tests/test_candidate_matcher.py tests/test_markdown_story_package.py tests/test_knowledge_leakage_matrix.py tests/test_leak_terms.py tests/test_canon_journey.py tests/test_must_convey.py tests/test_1c_reading_pointer.py 2>&1 | tail -15
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL tests"; exit 1; }
$PY -m ruff check tests/test_2c_assess_verbs.py && $PY -m ruff format --check tests/test_2c_assess_verbs.py || exit 1
echo PASS
