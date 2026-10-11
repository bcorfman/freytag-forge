#!/bin/bash
# Ringer check for the medical records scoped-alias change. Runs in the task worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
OUT=/home/bcorfman/dev/ringer-work/medical-records
N=$OUT-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
git add -A -- data tests .plans bench
bad=$(git status --porcelain | grep -v -E '^[AM]  (data/stories/continuity-initiative/world\.yaml|tests/.*|\.plans/disclosure-matrix\.(json|md)|bench/affordance_known_gaps\.json)$' || true)
[ -z "$bad" ] || { echo "FAIL stray paths:"; echo "$bad"; exit 1; }
mkdir -p "$OUT-patches"
git diff --cached > "$OUT-patches/medical.patch"
[ -s "$OUT-patches/medical.patch" ] || { echo "FAIL empty patch"; exit 1; }
git diff --cached -- data | grep -E '^[-+][^-+]' | grep -v -E 'aliases|medical records|survivor records' && { echo "FAIL data diff touches more than the item aliases"; exit 1; }
grep -q "scoped_aliases: \[medical records, survivor records\]" data/stories/continuity-initiative/world.yaml || { echo "FAIL scoped_aliases line missing"; exit 1; }
PYTHONPATH=$PWD TMPDIR=/tmp $PY -m pytest -q -p no:cacheprovider tests/test_medical_records_alias.py tests/test_3a_records_followup.py tests/test_disclosure_guards.py tests/test_disclosure_matrix.py 2>&1 | tail -15
[ ${PIPESTATUS[0]} -eq 0 ] || { echo "FAIL targeted tests"; exit 1; }
PYTHONPATH=$PWD TMPDIR=/tmp $PY -m pytest -q -p no:cacheprovider -n auto 2>&1 | tail -6
[ ${PIPESTATUS[0]} -eq 0 ] || { echo "FAIL full suite"; exit 1; }
$PY -m ruff check . && $PY -m ruff format --check . || exit 1
echo PASS
