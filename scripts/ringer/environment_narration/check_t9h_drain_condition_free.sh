#!/usr/bin/env bash
# Checks for the T9h drain condition experiment, steps 0 and 1 (free: no network, no model call).
# Usage: check_t9h_drain_condition_free.sh corpus|heldout
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
ED=scripts/ringer/environment_narration
TASK="${1:-}"
SCRATCH=/tmp/t9h-drain-condition-$TASK
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

case "$TASK" in
  corpus) SRC="$ED/drain_condition_corpus.py"; TEST=tests/test_drain_condition_corpus.py ;;
  heldout) SRC="$ED/drain_condition_heldout.py $ED/x1_condition_count.py"; TEST="tests/test_drain_condition_heldout.py tests/test_x1_condition_count.py" ;;
  *) echo "usage: check_t9h_drain_condition_free.sh corpus|heldout" >&2; exit 2 ;;
esac
for f in $SRC $TEST; do [ -f "$f" ] || { echo "FAIL: missing $f" >&2; exit 1; }; done
"$PY" -m pytest -q -p no:cacheprovider --no-cov $TEST > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check $SRC $TEST || exit 1
"$PY" -m ruff format --check $SRC $TEST || exit 1

if [ "$TASK" = corpus ]; then
  "$PY" "$ED/drain_condition_corpus.py" --build --out "$SCRATCH/corpus" || { echo "FAIL: --build" >&2; exit 1; }
  "$PY" "$ED/drain_condition_corpus.py" --blind-sheet --corpus "$SCRATCH/corpus/corpus.json" --out "$SCRATCH/sheet" || { echo "FAIL: --blind-sheet" >&2; exit 1; }
  "$PY" - "$SCRATCH" <<'PY' || exit 1
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
corpus = json.loads((root / "corpus" / "corpus.json").read_text())
rows = corpus["rows"]
labeled = [r for r in rows if r.get("provisional_label") is not None]
forbidden = [r for r in labeled if r["provisional_label"]["forbidden"]]
print(f"rows={len(rows)} labeled={len(labeled)} forbidden={len(forbidden)} clean={len(labeled)-len(forbidden)}")
assert len(labeled) == 49 and len(forbidden) == 18, "the 49 provisional labels (18 forbidden) must carry over exactly"
assert len(rows) >= 90, "expected the latency, ON/OFF smoke and screen/confirmation rows too"
assert len({r["id"] for r in rows}) == len(rows), "duplicate ids"
sheet = (root / "sheet" / "blind_sheet.md").read_text().lower()
for word in ("control", "candidate", "provisional", "forbidden", "t9h-", "rows.json", "smoke", "hedge", "latency"):
    assert word not in sheet, "blind sheet leaks: " + word
assert (root / "sheet" / "blind_key.json").is_file()
print("corpus build and blind sheet ok")
PY
fi
if [ "$TASK" = heldout ]; then
  "$PY" "$ED/drain_condition_heldout.py" --build --out "$SCRATCH/heldout" || { echo "FAIL: heldout --build" >&2; exit 1; }
  "$PY" "$ED/drain_condition_heldout.py" --blind-sheet --heldout "$SCRATCH/heldout/heldout.json" --out "$SCRATCH/heldout/sheet" || { echo "FAIL: heldout --blind-sheet" >&2; exit 1; }
  "$PY" "$ED/x1_condition_count.py" --corpus-build-only --out "$SCRATCH/x1" || { echo "FAIL: x1 count" >&2; exit 1; }
  "$PY" - "$SCRATCH" <<'PY' || exit 1
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
held = json.loads((root / "heldout" / "heldout.json").read_text())
rows = held["rows"]
things = {r["thing"] for r in rows}
print(f"heldout rows={len(rows)} things={sorted(things)[:12]}")
assert len(rows) >= 40 and len(things) >= 3 and "storm drain" not in things
assert all(r.get("narration") and r.get("source") for r in rows)
assert sum(1 for r in rows if r.get("authored")) <= 14
with_state = [r for r in rows if r.get("declared_state") is not None]
print(f"heldout rows with declared_state={len(with_state)} of {len(rows)}")
assert len(with_state) >= 30, "at least 30 held-out rows need a recorded declared state"
labelable = [r for r in rows if r.get("labelable") is True]
print(f"heldout labelable rows={len(labelable)}")
assert len(labelable) >= 30, "at least 30 rows need command, declared state and engine-open evidence"
for r in labelable:
    assert r.get("command") and r.get("engine_opened") in (True, False) and "open_state_after" in r, r["id"]
assert "the the object" not in (root / "heldout" / "sheet" / "blind_sheet.md").read_text(), "masking garbles the text"
assert "command:" in (root / "heldout" / "sheet" / "blind_sheet.md").read_text().lower(), "sheet must show the command"
assert all(isinstance(r["declared_state"], dict) and r["declared_state"].get("source") for r in with_state)
sheet = (root / "heldout" / "sheet" / "blind_sheet.md").read_text().lower() if (root / "heldout" / "sheet" / "blind_sheet.md").is_file() else ""
assert "declared" in sheet, "the blind sheet must show the declared state beside each narration"
for thing in things:
    assert thing.lower() not in sheet, "blind sheet leaks thing name: " + thing
x1 = json.loads((root / "x1" / "x1_count.json").read_text())
assert x1["labeled_forbidden"] == 18 and x1["labeled_clean"] == 31, x1
print("x1:", {k: x1[k] for k in ("labeled_forbidden", "forbidden_with_condition", "labeled_clean", "clean_with_condition")})
assert x1["forbidden_with_condition"] == 11 and x1["clean_with_condition"] == 0, "must reproduce the 11/18 and 0/31 measurement"
PY
fi
echo "drain condition $TASK checks ok"
