#!/usr/bin/env bash
# Checks for the T9h drain-rejection probe build tasks. Free: no network, no model call.
# Usage: check_t9h_drain_rejection_probes.sh replay|screen
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
TASK="${1:-}"
SCRATCH=/tmp/t9h-drain-probe-$TASK
ED=scripts/ringer/environment_narration
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

case "$TASK" in
  replay)
    SCRIPT=$ED/drain_replay_probe.py
    TEST=tests/test_drain_replay_probe.py
    PREREG=.plans/grounded-llm-environment-narration/t9h-drain-replay-prereg.md
    WRAPPER=$ED/enforce_t9h_drain_replay.sh
    CALLS=60
    USD=0.005
    ;;
  screen)
    SCRIPT=$ED/drain_details_prose_probe.py
    TEST=tests/test_drain_details_prose_probe.py
    PREREG=.plans/grounded-llm-environment-narration/t9h-drain-details-prereg.md
    WRAPPER=$ED/enforce_t9h_drain_details.sh
    CALLS=20
    USD=0.03
    ;;
  *) echo "usage: check_t9h_drain_rejection_probes.sh replay|screen" >&2; exit 2 ;;
esac

for f in "$SCRIPT" "$TEST" "$PREREG" "$WRAPPER"; do [ -f "$f" ] || { echo "FAIL: missing $f" >&2; exit 1; }; done
"$PY" -m pytest -q -p no:cacheprovider --no-cov "$TEST" > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check "$SCRIPT" "$TEST" || exit 1
"$PY" -m ruff format --check "$SCRIPT" "$TEST" || exit 1
bash -n "$WRAPPER" || { echo "FAIL: wrapper syntax" >&2; exit 1; }

"$PY" "$SCRIPT" --validate > "$SCRATCH/validate.out" 2>&1 || { cat "$SCRATCH/validate.out"; echo "FAIL: --validate" >&2; exit 1; }
"$PY" "$SCRIPT" --dry-run --max-calls "$CALLS" --max-usd "$USD" > "$SCRATCH/dry.out" 2>&1 || { cat "$SCRATCH/dry.out"; echo "FAIL: --dry-run within the cap" >&2; exit 1; }
cat "$SCRATCH/dry.out" | head -20
grep -q "$CALLS" "$SCRATCH/dry.out" || { echo "FAIL: dry run does not print the planned call count $CALLS" >&2; exit 1; }
if "$PY" "$SCRIPT" --dry-run --max-calls 1 --max-usd 0.0000001 > "$SCRATCH/tight.out" 2>&1; then
  echo "FAIL: a too-small cap was accepted" >&2
  exit 1
fi
if "$PY" "$SCRIPT" --run --max-calls "$CALLS" --max-usd "$USD" > "$SCRATCH/noconfirm.out" 2>&1; then
  echo "FAIL: --run without --confirm was accepted" >&2
  exit 1
fi
grep -qi "frozen\|before.*scor" "$PREREG" || { echo "FAIL: prereg lacks the freeze statement" >&2; exit 1; }
grep -q "$CALLS" "$PREREG" || { echo "FAIL: prereg lacks the call count" >&2; exit 1; }
echo "drain probe $TASK checks ok"
