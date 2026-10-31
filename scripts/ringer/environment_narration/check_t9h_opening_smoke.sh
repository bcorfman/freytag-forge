#!/usr/bin/env bash
# Integrity check for the billed T9h opening-check smoke: summaries written, opening verdicts recorded, no credential leak.
set -uo pipefail
STAGE="${1:-smoke}"
ROOT=/home/bcorfman/dev/freytag-forge
cd "$ROOT" || exit 2
(set -a; . ./.env; set +a; "$ROOT/.venv/bin/python" - "$STAGE" <<'PY'
import json
import os
import sys
from pathlib import Path

out = Path("bench/results/environment-narration/t9h-opening-check") / sys.argv[1]
errors, text = [], ""
for route in ("observe_storm_drain_1b", "observe_service_gate_1b", "observe_back_door_1a"):
    summary = out / route / "rows/summary.json"
    rows = out / route / "rows/rows.json"
    if not summary.exists():
        errors.append(f"{route}: summary.json missing"); continue
    doc = json.loads(summary.read_text())
    print(route, "stopped_reason:", doc.get("stopped_reason"))
    text += summary.read_text() + (rows.read_text() if rows.exists() else "")
    if rows.exists() and "opening_verdicts" not in rows.read_text():
        errors.append(f"{route}: no opening_verdicts recorded")
if (out / "worker.log").exists():
    text += (out / "worker.log").read_text()
    print("worker:", (out / "worker.log").read_text().strip().splitlines()[-1])
for name in ("CLOUDFLARE_AI_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_WORKER_TOKEN", "OPENAI_API_KEY", "RAILWAY_TOKEN"):
    value = os.environ.get(name, "").strip()
    if value and value in text:
        errors.append(f"{name} leaked")
if errors:
    print("FAIL:\n  " + "\n  ".join(errors)); sys.exit(1)
print("PASS (integrity only)")
PY
)
