#!/usr/bin/env bash
# Check for the T9h drain condition judge probe build (Step 2). Free: no network, no model call.
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
ED=scripts/ringer/environment_narration
SCRIPT=$ED/drain_condition_judge_probe.py
TEST=tests/test_drain_condition_judge_probe.py
WRAPPER=$ED/enforce_t9h_drain_condition_judge.sh
PREREG=.plans/grounded-llm-environment-narration/t9h-drain-condition-judge-prereg.md
CASES=$ED/drain_condition_judge/cases.jsonl
LOCK=$ED/drain_condition_judge/lock.json
SCRATCH=/tmp/t9h-drain-condition-judge
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

for f in "$SCRIPT" "$TEST" "$WRAPPER" "$PREREG" "$CASES" "$LOCK"; do [ -f "$f" ] || { echo "FAIL: missing $f" >&2; exit 1; }; done
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
"$PY" "$SCRIPT" --dry-run --max-calls 2100 --max-usd 0.06 > "$SCRATCH/dry.out" 2>&1 || { cat "$SCRATCH/dry.out"; echo "FAIL: --dry-run within the cap" >&2; exit 1; }
cat "$SCRATCH/dry.out" | head -20
grep -q "2100" "$SCRATCH/dry.out" || { echo "FAIL: dry run does not print 2100 planned calls" >&2; exit 1; }
if "$PY" "$SCRIPT" --dry-run --max-calls 10 --max-usd 0.0000001 > "$SCRATCH/tight.out" 2>&1; then echo "FAIL: too-small cap accepted" >&2; exit 1; fi
if "$PY" "$SCRIPT" --run --max-calls 2100 --max-usd 0.06 --out "$SCRATCH/rows.json" > "$SCRATCH/noconfirm.out" 2>&1; then echo "FAIL: --run without --confirm accepted" >&2; exit 1; fi

"$PY" - <<'PY' || exit 1
import json
from pathlib import Path

cases = [json.loads(line) for line in Path("scripts/ringer/environment_narration/drain_condition_judge/cases.jsonl").read_text().splitlines() if line.strip()]
drain = [c for c in cases if c["set"] == "drain"]
held = [c for c in cases if c["set"] == "heldout"]
f = lambda rows: sum(1 for c in rows if c["forbidden"])
print(f"cases={len(cases)} drain={len(drain)} (forbidden {f(drain)}) heldout={len(held)} (forbidden {f(held)})")
assert (len(drain), f(drain), len(held), f(held)) == (100, 54, 40, 10), "case counts must match the frozen corpora"
assert len({c["id"] for c in cases}) == 140
for c in cases:
    assert c["narration"] and c["thing"] and c["command"] and c["declared"], c["id"]
    assert "open_state_after" not in json.dumps(c), "open_state_after must not reach the judge"
PY
prereg=$(cat "$PREREG")
for needle in "49 of 54" "42 of 46" "9 of 10" "27 of 30" "median" "2100" "0.06" "Variant B" "candidate" "frozen"; do
  printf '%s' "$prereg" | grep -qi "$needle" || { echo "FAIL: prereg lacks '$needle'" >&2; exit 1; }
done
grep -qi "darkness" "$PREREG" || { echo "FAIL: prereg variants must name the inside description (darkness, water, sounds, smells)" >&2; exit 1; }
grep -qi "darkness" "$SCRIPT" || { echo "FAIL: script variants must name the inside description" >&2; exit 1; }
"$PY" - <<'PY' || exit 1
from pathlib import Path

prereg = Path(".plans/grounded-llm-environment-narration/t9h-drain-condition-judge-prereg.md").read_text()
script = Path("scripts/ringer/environment_narration/drain_condition_judge_probe.py").read_text()
# Every instruction and criterion sentence in the prereg's quoted variant blocks must appear verbatim in the script.
quoted = [line[2:].strip() for line in prereg.splitlines() if line.startswith("> ")]
assert len(quoted) >= 7, quoted
for sentence in quoted:
    for part in sentence.split(". "):
        part = part.strip().rstrip(".")
        if len(part) > 25:
            assert part in script, "prereg sentence missing from the script: " + part
print("prereg variant text matches the script")
PY
echo "drain condition judge probe checks ok"
