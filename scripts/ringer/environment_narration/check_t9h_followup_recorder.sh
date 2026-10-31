#!/usr/bin/env bash
# Check for the Route E recorder task (story_facts_after). Free: no network, no model call.
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
FILES="scripts/ringer/transcript_1a/live_baseline.py tests/test_live_baseline_evidence.py scripts/ringer/environment_narration/hidden_clues_smoke_report.py tests/test_hidden_clues_smoke_report.py"
SCRATCH=/tmp/t9h-followup-recorder
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

"$PY" -m pytest -q -p no:cacheprovider --no-cov tests/test_live_baseline_evidence.py tests/test_hidden_clues_smoke_report.py tests/test_live_baseline_scene_start.py > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
# shellcheck disable=SC2086
"$PY" -m ruff check $FILES || exit 1
# shellcheck disable=SC2086
"$PY" -m ruff format --check $FILES || exit 1
grep -q "story_facts_after" scripts/ringer/transcript_1a/live_baseline.py || { echo "FAIL: runner does not record story_facts_after" >&2; exit 1; }
grep -q "story_facts_after" scripts/ringer/environment_narration/hidden_clues_smoke_report.py || { echo "FAIL: reporter does not read story_facts_after" >&2; exit 1; }
echo "recorder checks ok"
