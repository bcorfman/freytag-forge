#!/usr/bin/env bash
# Check for the hidden-thing audit tool task. Free: no network, no model call.
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
SCRIPT=scripts/hidden_thing_audit.py
TEST=tests/test_hidden_thing_audit.py
PACKAGE=data/stories/continuity-initiative
SCRATCH=/tmp/t9h-followup-audit
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
test -f "$SCRIPT" && test -f "$TEST" || { echo "FAIL: audit or test file missing" >&2; exit 1; }

before=$(find "$PACKAGE" -type f -exec sha256sum {} + | sort | sha256sum)
"$PY" -m pytest -q -p no:cacheprovider --no-cov "$TEST" > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check "$SCRIPT" "$TEST" || exit 1
"$PY" -m ruff format --check "$SCRIPT" "$TEST" || exit 1

"$PY" "$SCRIPT" "$PACKAGE" --out "$SCRATCH/audit.md" || { echo "FAIL: audit exited non-zero on the real package" >&2; exit 1; }
"$PY" "$SCRIPT" "$PACKAGE" --json --out "$SCRATCH/audit.json" || { echo "FAIL: --json audit failed" >&2; exit 1; }
"$PY" - "$SCRATCH/audit.json" <<'PY' || exit 1
import json
import sys

document = json.load(open(sys.argv[1], encoding="utf-8"))
text = json.dumps(document)
for item in ("memory_card", "transit_card", "number_sequence", "michelle_photograph", "override_codes", "prisoner_number_record"):
    assert item in text, f"audit does not list hidden item {item}"
print("audit lists all six hidden items")
PY
grep -qi "not checked" "$SCRATCH/audit.md" || { echo "FAIL: audit lacks its Not checked section" >&2; exit 1; }
after=$(find "$PACKAGE" -type f -exec sha256sum {} + | sort | sha256sum)
[ "$before" = "$after" ] || { echo "FAIL: the audit changed the story package" >&2; exit 1; }
echo "audit checks ok"
