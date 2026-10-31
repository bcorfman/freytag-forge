#!/usr/bin/env bash
# Check for the T9h stage 2 arm probe build task. Free: no network, no model call.
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
SCRIPT=scripts/ringer/environment_narration/hidden_bench_arm_probe.py
TEST=tests/test_hidden_bench_arm_probe.py
SCRATCH=/tmp/t9h-stage2-arm-probe
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

test -f "$SCRIPT" && test -f "$TEST" || { echo "FAIL: probe or test file missing" >&2; exit 1; }

"$PY" -m pytest -q -p no:cacheprovider --no-cov "$TEST" > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check "$SCRIPT" "$TEST" || exit 1
"$PY" -m ruff format --check "$SCRIPT" "$TEST" || exit 1

"$PY" "$SCRIPT" --capture --out "$SCRATCH/capture.json" || { echo "FAIL: capture" >&2; exit 1; }
"$PY" - "$SCRATCH/capture.json" <<'PY' || exit 1
import json
import sys

ids = {payload["id"] for payload in json.load(open(sys.argv[1], encoding="utf-8"))["payloads"]}
expected = {f"{arm}-{state}" for arm in ("base", "B") for state in ("opening", "inspect", "find")} | {"C-inspect", "C-find"}
assert ids == expected, f"payload ids {sorted(ids)} != {sorted(expected)}"
print("capture ok:", sorted(ids))
PY
"$PY" "$SCRIPT" --validate || { echo "FAIL: validate on the real package" >&2; exit 1; }
"$PY" "$SCRIPT" --dry-run | tee "$SCRATCH/dry.out" || { echo "FAIL: dry-run" >&2; exit 1; }
grep -q "planned calls: 30" "$SCRATCH/dry.out" || { echo "FAIL: dry-run must plan 30 calls" >&2; exit 1; }
"$PY" "$SCRIPT" --run --out "$SCRATCH/rows.json" > /dev/null 2>&1 && { echo "FAIL: --run must refuse without --confirm and credentials" >&2; exit 1; }
test ! -e "$SCRATCH/rows.json" || { echo "FAIL: a refused run wrote rows" >&2; exit 1; }

# The real story package must be untouched by this task.
grep -q "ordinary park bench; damaged grounds" data/stories/continuity-initiative/plot.md || { echo "FAIL: real plot.md Details line changed" >&2; exit 1; }
echo "arm probe checks ok"
