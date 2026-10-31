#!/usr/bin/env bash
# Check for the billed T9h opening v2 judge run: complete rows, a report with a verdict, no credential leak.
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
cd "$ROOT" || exit 2
(set -a; . ./.env; set +a; "$ROOT/.venv/bin/python" - <<'PY'
import json
import os
import sys
from pathlib import Path

out = Path("bench/results/environment-narration/t9h-opening-v2")
rows_path, report = out / "judge/rows.json", out / "report.md"
errors = []
if not rows_path.exists():
    print(f"FAIL: {rows_path} missing"); sys.exit(1)
doc = json.loads(rows_path.read_text())
print(f"rows {len(doc.get('rows', []))} of {doc.get('calls_planned')}, stop_reason {doc.get('stop_reason')!r}")
if len(doc.get("rows", [])) != 200 and doc.get("stop_reason") is None:
    errors.append("incomplete rows without a stop reason")
if not report.exists():
    errors.append("report.md missing")
else:
    text = report.read_text()
    if not any(word in text for word in ("PASS", "FAIL", "INCONCLUSIVE")):
        errors.append("report has no verdict")
text = rows_path.read_text() + (out / "judge/worker.log").read_text() if (out / "judge/worker.log").exists() else rows_path.read_text()
for name in ("CLOUDFLARE_AI_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_WORKER_TOKEN", "OPENAI_API_KEY", "RAILWAY_TOKEN"):
    value = os.environ.get(name, "").strip()
    if value and value in text:
        errors.append(f"{name} leaked")
if errors:
    print("FAIL:\n  " + "\n  ".join(errors)); sys.exit(1)
print("PASS (integrity only; the verdict is in report.md)")
PY
)
