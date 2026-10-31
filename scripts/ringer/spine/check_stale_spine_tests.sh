#!/usr/bin/env bash
# Ringer check for the stale-spine-tests task. Prints why it fails.
set -uo pipefail
cd /home/bcorfman/dev/freytag-forge
test ! -e tests/test_1c_spine_prompts.py || { echo "test_1c_spine_prompts.py still exists"; exit 1; }
if grep -nE '\bmatching_reveals\b|\bexpected_reveals\(' tests/*.py; then echo "removed generator names still referenced"; exit 1; fi
grep -q "def test_research_fragments_then_files_can_both_be_earned" tests/test_1a_spine_prompts.py || { echo "kept eligibility test was removed"; exit 1; }
TMPDIR=/tmp uv run pytest -q --no-cov -p no:cacheprovider tests/test_1a_spine_prompts.py tests/test_spine_expected_reveals.py tests/test_canon_journey.py || exit 1
uv run ruff check . && uv run ruff format --check . | tail -1
