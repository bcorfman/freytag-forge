#!/usr/bin/env bash
# Check for stage 2 item 1: jev_stats in the bench summary. Runs inside the task worktree.
set -u
cd "$(pwd)"
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
export TMPDIR=/tmp
git add -A >/dev/null 2>&1
git diff --cached --name-only | grep -Ev '^(bench/cli\.py|tests/test_bench\.py|tests/test_jev_summary\.py)$' | sed 's/^/UNOWNED FILE CHANGED: /' | tee /tmp/stage2_unowned.txt
[ -s /tmp/stage2_unowned.txt ] && exit 1
git diff --cached --quiet -- bench/cli.py && { echo "bench/cli.py has no change"; exit 1; }
grep -q "jev_stats" bench/cli.py || { echo "bench/cli.py never uses jev_stats"; exit 1; }
test -f tests/test_jev_summary.py || { echo "missing tests/test_jev_summary.py"; exit 1; }
PYTHONPATH=$PWD $PY -m pytest -q --no-cov -p no:cacheprovider tests/test_jev_summary.py tests/test_jev_use.py tests/test_bench.py 2>&1 | tail -25 || exit 1
PYTHONPATH=$PWD $PY -m pytest -q --no-cov -p no:cacheprovider tests/test_jev_summary.py tests/test_jev_use.py tests/test_bench.py >/dev/null 2>&1 || { echo "pytest failed"; exit 1; }
$PY -m ruff check bench tests/test_jev_summary.py && $PY -m ruff format --check bench tests/test_jev_summary.py || exit 1
git diff --cached > /home/bcorfman/dev/ringer-work/stage2-notes/jev-summary.patch
test -s /home/bcorfman/dev/ringer-work/stage2-notes/jev-summary.patch || { echo "empty patch"; exit 1; }
