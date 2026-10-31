#!/usr/bin/env bash
# Check for the drain-details probe freeze fix and confirmation stage. Free: no network, no model call.
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
ED=scripts/ringer/environment_narration
SCRIPT=$ED/drain_details_prose_probe.py
TEST=tests/test_drain_details_prose_probe.py
WRAPPER=$ED/enforce_t9h_drain_details.sh
PREREG=.plans/grounded-llm-environment-narration/t9h-drain-details-prereg.md
SCRATCH=/tmp/t9h-drain-details-confirm
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

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
"$PY" "$SCRIPT" --dry-run --samples 10 --max-calls 20 --max-usd 0.03 > "$SCRATCH/dry10.out" 2>&1 || { cat "$SCRATCH/dry10.out"; echo "FAIL: screen dry-run" >&2; exit 1; }
"$PY" "$SCRIPT" --dry-run --samples 15 --max-calls 30 --max-usd 0.06 > "$SCRATCH/dry15.out" 2>&1 || { cat "$SCRATCH/dry15.out"; echo "FAIL: confirm dry-run" >&2; exit 1; }
cat "$SCRATCH/dry15.out"
grep -q "planned calls: 30" "$SCRATCH/dry15.out" || { echo "FAIL: confirm dry-run does not plan 30 calls" >&2; exit 1; }
grep -q "confirm" "$WRAPPER" || { echo "FAIL: wrapper has no confirm stage" >&2; exit 1; }
grep -q "8805" "$WRAPPER" || { echo "FAIL: confirm stage should use its own port 8805" >&2; exit 1; }
grep -Eq 'confirmation.*0\.06|0\.06.*confirmation' "$PREREG" || { echo "FAIL: prereg lacks the dated confirmation addendum with the 0.06 cap" >&2; exit 1; }

# Freeze flow: --sheets must NOT write a freeze hash of the empty template; --freeze-labels must.
"$PY" - <<'PY' || exit 1
import json
import tempfile
from pathlib import Path

from scripts.ringer.environment_narration import drain_details_prose_probe as probe

with tempfile.TemporaryDirectory() as raw:
    out = Path(raw)
    rows = out / "rows.json"
    rows.write_text(json.dumps({"rows": [{"payload_id": "control", "arm": "control", "sample": 1, "response_text": "x"}]}))
    probe.sheets(rows, out / "sheet")
    assert not (out / "sheet" / "labels.freeze.json").exists(), "sheets still freezes the empty template"
print("freeze flow ok")
PY
echo "drain details confirm checks ok"
