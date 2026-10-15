#!/usr/bin/env bash
# Check for astra-a3-merge. Runs inside the Ringer worktree.
set -u
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-a3-merge-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
main_bad=$(git -C /home/bcorfman/dev/freytag-forge status --porcelain | grep -v -E "scripts/ringer/astra/|\.plans/" || true)
[ -z "$main_bad" ] || { echo "FAIL main checkout modified:"; echo "$main_bad"; exit 1; }
git add -A -- bench tests scripts/ringer/astra/p4-refusal-measure-check.sh scripts/ringer/astra/refusal_summary.py
bad=$(git status --porcelain | grep -v node_modules | grep -v -E '^(A|M)  (bench/(jev_use\.py|pipeline_eval/(metrics|model|runner)\.py)|tests/test_(jev_use|pipeline_eval|pipeline_eval_cases|refusal_checker)\.py|scripts/ringer/astra/(p4-refusal-measure-check\.sh|refusal_summary\.py))$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
ls bench/pipeline_eval/test_*.py >/dev/null 2>&1 && { echo "FAIL tests left under bench/pipeline_eval (testpaths is tests/):"; ls bench/pipeline_eval/test_*.py; exit 1; }
OUT=/home/bcorfman/dev/ringer-work/astra-patches; mkdir -p "$OUT"
git diff --cached > "$OUT/a3-merged.patch"
[ -s "$OUT/a3-merged.patch" ] || { echo "FAIL empty patch"; exit 1; }
for f in tests/test_refusal_checker.py scripts/ringer/astra/refusal_summary.py; do [ -e $f ] || { echo "FAIL missing $f"; exit 1; }; done
export PYTHONPATH=$PWD TMPDIR=/tmp
$PY -c "import storygame,sys; sys.exit(0 if storygame.__file__.startswith('$PWD') else 1)" || { echo "FAIL storygame not from worktree"; exit 1; }
$PY -m pytest -q -p no:cacheprovider --no-cov -x tests 2>&1 | tail -10
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL suite"; exit 1; }
$PY -m ruff check storygame tests bench scripts/ringer/astra/refusal_summary.py && $PY -m ruff format --check storygame tests bench scripts/ringer/astra/refusal_summary.py || exit 1
bash -n scripts/ringer/astra/p4-refusal-measure-check.sh || { echo "FAIL checker script syntax"; exit 1; }
echo PASS
