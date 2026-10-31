#!/usr/bin/env bash
# Check for the paced complete-run setup of the T9h drain condition judge probe. Free: no network, no model call.
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
ED=scripts/ringer/environment_narration
SCRIPT=$ED/drain_condition_judge_probe.py
WRAPPER=$ED/enforce_t9h_drain_condition_judge.sh
PREREG=.plans/grounded-llm-environment-narration/t9h-drain-condition-judge-prereg.md
SCRATCH=/tmp/t9h-drain-condition-judge-rerun
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

# The original build check (tests, ruff, validate, 2100-call dry run under 0.06, prereg text equals code) must still pass.
bash "$ED/check_t9h_drain_condition_judge.sh" > "$SCRATCH/base.out" 2>&1 || { tail -30 "$SCRATCH/base.out"; echo "FAIL: base check" >&2; exit 1; }

# Cases and gate are frozen: the hash must be exactly the one the first run used.
want=c5387f4236bb386e52c690dc702ff28143b0b3ab4540594fcf20f12c1cff669b
got=$(sha256sum $ED/drain_condition_judge/cases.jsonl | cut -d' ' -f1)
[ "$got" = "$want" ] || { echo "FAIL: cases.jsonl changed ($got)" >&2; exit 1; }

"$PY" "$SCRIPT" --dry-run --max-calls 2100 --max-usd 0.08 --min-interval-s 0.5 > "$SCRATCH/dry.out" 2>&1 || { cat "$SCRATCH/dry.out"; echo "FAIL: paced dry-run" >&2; exit 1; }
cat "$SCRATCH/dry.out" | head -12
grep -qi "interval" "$SCRATCH/dry.out" || { echo "FAIL: dry run does not show the pacing interval" >&2; exit 1; }
if "$PY" "$SCRIPT" --dry-run --max-calls 2100 --max-usd 0.08 --min-interval-s -1 > "$SCRATCH/neg.out" 2>&1; then echo "FAIL: negative interval accepted" >&2; exit 1; fi
if "$PY" "$SCRIPT" --run --max-calls 2100 --max-usd 0.08 --min-interval-s 0.5 --out "$SCRATCH/rows.json" > "$SCRATCH/noconfirm.out" 2>&1; then echo "FAIL: --run without --confirm accepted" >&2; exit 1; fi

grep -q "judge2" "$WRAPPER" || { echo "FAIL: wrapper has no judge2 stage" >&2; exit 1; }
grep -q "step2-complete" "$WRAPPER" || { echo "FAIL: judge2 must write to the fresh step2-complete directory" >&2; exit 1; }
grep -q "8810" "$WRAPPER" || { echo "FAIL: judge2 should use port 8810" >&2; exit 1; }
grep -q "0.08" "$WRAPPER" || { echo "FAIL: judge2 cap 0.08 missing" >&2; exit 1; }
grep -q "min-interval-s" "$WRAPPER" || { echo "FAIL: judge2 must pass the pacing interval" >&2; exit 1; }
# The first run's wrapper stage and its rows directory must be untouched.
grep -q "t9h-drain-condition/step2\"" "$WRAPPER" || { echo "FAIL: the original judge stage's output path changed" >&2; exit 1; }
[ ! -e bench/results/environment-narration/t9h-drain-condition/step2-complete ] || { echo "FAIL: step2-complete already exists" >&2; exit 1; }

pre=$(cat "$PREREG")
for needle in "Addendum" "rate limit" "429" "pacing" "0.08" "step2-complete" "246" "49 of 54" "Variant B" "no cases, variants, labels or gate numbers changed"; do
  printf '%s' "$pre" | grep -qi "$needle" || { echo "FAIL: prereg addendum lacks '$needle'" >&2; exit 1; }
done
echo "drain condition judge rerun setup checks ok"
