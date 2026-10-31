#!/usr/bin/env bash
# Checks for T9h section 16: Variant D wording (looking into a dark opening is allowed) and its judge run.
# Usage: check_t9h_opening_v3.sh build|judge [v3|v4]  (v3 = Variant D, section 16; v4 = Variant E, section 17)
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
TASK="${1:?build|judge}"
VERSION="${2:-v3}"
case "$VERSION" in
  v3) QUESTION=variant-d-question.json ;;
  v4) QUESTION=variant-e-question.json ;;
  *) echo "unknown version $VERSION" >&2; exit 2 ;;
esac
export VERSION QUESTION
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
OUT=bench/results/environment-narration/t9h-opening-$VERSION

case "$TASK" in
  build)
    unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
    "$PY" - <<'PY' || exit 1
import hashlib, json, os, sys
from pathlib import Path
from storygame.runtime import opening_check
version, question = os.environ["VERSION"], os.environ["QUESTION"]
base = Path("scripts/ringer/environment_narration/drain_condition_judge")
errors = []
expected = json.loads((base / question).read_text())
if opening_check.OPENING_QUESTION != expected:
    errors.append("runtime OPENING_QUESTION is not byte-identical to " + question)
state, questions = opening_check.opening_payload("n", "storm drain", "inspect the storm drain")
if set(state) != {"narration", "thing", "command", "declared"} or state["declared"] != (
    "the storm drain has no open or closed value, no declared contents, and is fixed in place."
):
    errors.append(f"runtime state changed: {state}")
if version == "v4":
    story = "The back door was forced."
    try:
        state, _ = opening_check.opening_payload("n", "back door", "inspect the back door", story_text=story)
    except TypeError as error:
        errors.append(f"opening_payload has no story_text keyword: {error}")
    else:
        want = "the back door has no open or closed value, no declared contents, and is fixed in place. The story states: The back door was forced."
        if state.get("declared") != want:
            errors.append(f"declared sentence with story text is {state.get('declared')!r}, want {want!r}")
data = (base / f"cases-{version}.jsonl").read_bytes()
lock = json.loads((base / f"lock-{version}.json").read_text())
if lock != {"cases_sha256": hashlib.sha256(data).hexdigest(), "case_count": 180}:
    errors.append(f"cases-{version}.jsonl does not match lock-{version}.json (the case file must not be edited)")
if hashlib.sha256((base / "cases.jsonl").read_bytes()).hexdigest() != json.loads((base / "lock.json").read_text())["cases_sha256"]:
    errors.append("the Step 2 cases.jsonl was modified")
if errors:
    print("FAIL:\n  " + "\n  ".join(errors)); sys.exit(1)
print("wording and frozen cases OK")
PY
    "$PY" scripts/ringer/environment_narration/opening_condition_v3.py --dry-run --max-usd 0.05 --cases "scripts/ringer/environment_narration/drain_condition_judge/cases-$VERSION.jsonl" --lock "scripts/ringer/environment_narration/drain_condition_judge/lock-$VERSION.json" || { echo "FAIL: dry run" >&2; exit 1; }
    bash scripts/ringer/ci_sim_pytest.sh -n 8 tests/test_opening_check.py tests/test_opening_condition_v3.py \
      tests/test_drain_condition_judge_probe.py tests/test_observation_verifier.py tests/test_opening_retry.py \
      tests/test_opening_retry_fact.py tests/test_opening_things_fact.py tests/test_live_baseline_opening_check.py \
      tests/test_opening_condition_v2.py > /tmp/opening-v3-build.out 2>&1; rc=$?
    grep -E "^(FAILED|ERROR)|passed|failed" /tmp/opening-v3-build.out | tail -20
    [ $rc -eq 0 ] || { echo "FAIL: tests" >&2; exit 1; }
    "$PY" -m ruff check storygame/runtime/opening_check.py scripts/ringer/environment_narration/opening_condition_v3.py tests/test_opening_check.py tests/test_opening_condition_v3.py || exit 1
    "$PY" -m ruff format --check storygame/runtime/opening_check.py scripts/ringer/environment_narration/opening_condition_v3.py tests/test_opening_check.py tests/test_opening_condition_v3.py || exit 1
    echo PASS
    ;;
  judge)
    (set -a; . ./.env; set +a; "$PY" - <<'PY'
import json, os, sys
from pathlib import Path
out = Path("bench/results/environment-narration/t9h-opening-" + os.environ["VERSION"])
errors = []
rows_path = out / "judge/rows.json"
if not rows_path.exists():
    print("FAIL: judge/rows.json missing"); sys.exit(1)
doc = json.loads(rows_path.read_text())
print("rows:", len(doc.get("rows", [])), "of", doc.get("calls_planned"), "stop_reason:", doc.get("stop_reason"))
if not (out / "report.md").exists():
    errors.append("report.md missing")
text = rows_path.read_text() + ((out / "report.md").read_text() if (out / "report.md").exists() else "")
for p in out.rglob("*.log"):
    text += p.read_text()
for name in ("CLOUDFLARE_AI_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_WORKER_TOKEN", "OPENAI_API_KEY", "RAILWAY_TOKEN"):
    value = os.environ.get(name, "").strip()
    if value and value in text:
        errors.append(f"{name} leaked")
if errors:
    print("FAIL:\n  " + "\n  ".join(errors)); sys.exit(1)
print("PASS (integrity only)")
PY
    )
    ;;
  *) echo "usage: check_t9h_opening_v3.sh build|judge [v3|v4]" >&2; exit 2 ;;
esac
