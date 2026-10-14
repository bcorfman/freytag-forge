#!/usr/bin/env bash
# Check for astra-a3-gates tasks. Usage: check_a3.sh KEY   (KEY = checker | jev | runner). Runs inside the Ringer worktree.
set -u
KEY=$1
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-a3-$KEY-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
main_bad=$(git -C /home/bcorfman/dev/freytag-forge status --porcelain | grep -v -E "scripts/ringer/astra/|\.plans/" || true)
[ -z "$main_bad" ] || { echo "FAIL main checkout modified:"; echo "$main_bad"; exit 1; }
case $KEY in
  checker) PATHS="scripts/ringer/astra"; ALLOW='scripts/ringer/astra/[A-Za-z0-9_./-]+\.(sh|py)'; TESTS="bench/pipeline_eval/test_refusal_checker.py" ;;
  jev)     PATHS="bench"; ALLOW='bench/(jev_use\.py|pipeline_eval/test_[A-Za-z0-9_]+\.py)'; TESTS="bench/pipeline_eval/test_jev_use.py" ;;
  runner)  PATHS="bench"; ALLOW='bench/pipeline_eval/[A-Za-z0-9_]+\.(py|json)'; TESTS="bench/pipeline_eval" ;;
  *) echo "FAIL unknown key $KEY"; exit 1 ;;
esac
git add -A -- $PATHS
bad=$(git status --porcelain | grep -v node_modules | grep -v -E "^(A|M)  ($ALLOW)\$" || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
OUT=/home/bcorfman/dev/ringer-work/astra-patches; mkdir -p "$OUT"
git diff --cached > "$OUT/a3-$KEY.patch"
[ -s "$OUT/a3-$KEY.patch" ] || { echo "FAIL empty patch"; exit 1; }
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not from worktree"; exit 1; }
for t in $TESTS; do [ -e "$t" ] || { echo "FAIL missing $t"; exit 1; }; done
$PY -m pytest -q -p no:cacheprovider --no-cov $TESTS 2>&1 | tail -15
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL task tests"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov -x tests bench/pipeline_eval 2>&1 | tail -8
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL suite"; exit 1; }
$PY -m ruff check storygame tests bench && $PY -m ruff format --check storygame tests bench || exit 1
bash -n scripts/ringer/astra/p4-refusal-measure-check.sh || { echo "FAIL checker script syntax"; exit 1; }
echo PASS
