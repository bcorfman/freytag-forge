#!/bin/bash
# Check for the pipeline-eval widen task. Runs inside the worker's git worktree.
set -u
MAIN=/home/bcorfman/dev/freytag-forge
PY=$MAIN/.venv/bin/python
N=/home/bcorfman/dev/ringer-work/astra-pipeline-eval-widen-notes/notes.md
OUT=/home/bcorfman/dev/ringer-work/astra-patches
PATHS="bench/pipeline_eval tests/test_pipeline_eval.py tests/test_pipeline_eval_cases.py"

[ -s "$N" ] || { echo "FAIL no notes"; exit 1; }
git add -A -- $PATHS
bad=$(git status --porcelain | grep -v -E '^[AM]  (bench/pipeline_eval/[A-Za-z_.]+|tests/test_pipeline_eval(_cases)?\.py)$' || true)
[ -z "$bad" ] || { echo "FAIL stray files:"; echo "$bad"; exit 1; }
mkdir -p "$OUT"
git diff --cached > "$OUT/pipeline-eval-widen.patch"
[ -s "$OUT/pipeline-eval-widen.patch" ] || { echo "FAIL empty patch"; exit 1; }
main_dirty=$(cd $MAIN && git status --porcelain)
[ -z "$main_dirty" ] || { echo "FAIL worker wrote into the main checkout:"; echo "$main_dirty"; exit 1; }
if grep -rn -i -E 'cloudflare|openai|httpx|urllib|load_dotenv|CLOUDFLARE_|OPENAI_' bench/pipeline_eval; then
  echo "FAIL billed or network reference"; exit 1
fi
$PY $MAIN/scripts/ringer/astra/check_widen_cases.py bench/pipeline_eval/cases.json || exit 1
PYTHONPATH=$PWD TMPDIR=/tmp $PY -m pytest -q -p no:cacheprovider --no-cov tests/test_pipeline_eval.py tests/test_pipeline_eval_cases.py 2>&1 | tail -20
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL tests"; exit 1; }
PYTHONPATH=$PWD $PY -m bench.pipeline_eval smoke > /dev/null || { echo "FAIL smoke"; exit 1; }
PYTHONPATH=$PWD $PY -m bench.pipeline_eval report --cases bench/pipeline_eval/cases.json | tail -3
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL report"; exit 1; }
$PY -m ruff check $PATHS && $PY -m ruff format --check $PATHS || exit 1
echo PASS
