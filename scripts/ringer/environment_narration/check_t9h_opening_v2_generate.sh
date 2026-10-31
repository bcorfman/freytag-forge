#!/usr/bin/env bash
# Check for the billed T9h opening v2 generation: 40 complete rows, every narration non-empty.
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
cd "$ROOT" || exit 2
"$ROOT/.venv/bin/python" - <<'PY' || exit 1
import json
import sys
from pathlib import Path

out = Path("bench/results/environment-narration/t9h-opening-v2")
rows_path = out / "generate-2/rows.json"
if not rows_path.exists():
    print(f"FAIL: {rows_path} missing"); sys.exit(1)
doc = json.loads(rows_path.read_text())
rows = doc.get("rows", [])
errors = []
if doc.get("stop_reason") is not None:
    errors.append(f"stop_reason {doc.get('stop_reason')!r} (partial run; do not rerun, report it)")
if len(rows) != 40:
    errors.append(f"{len(rows)} rows, expected 40")
if len(set((r.get("thing_id"), r.get("sample")) for r in rows)) != len(rows):
    errors.append("duplicate thing/sample rows")
print("failed calls:", [(c.get("thing_id"), c.get("sample"), c.get("error_type")) for c in doc.get("failed_calls", [])])
counts = {}
for row in rows:
    counts[row.get("thing_id")] = counts.get(row.get("thing_id"), 0) + 1
    if not str(row.get("narration", "")).strip():
        errors.append(f"row {row.get('call_index')} has empty narration")
print("rows per thing:", counts)
spent = out / "generate-2/worker.log"
if spent.exists():
    print("worker log tail:", spent.read_text()[-400:])
if errors:
    print("FAIL:\n  " + "\n  ".join(errors)); sys.exit(1)
print("PASS")
PY
# Credentials must never reach the outputs.
(set -a; . ./.env; set +a; "$ROOT/.venv/bin/python" - <<'PY'
import os
import sys
from pathlib import Path

out = Path("bench/results/environment-narration/t9h-opening-v2")
text = "".join(p.read_text() for p in (out / "generate-2/rows.json", out / "generate-2/worker.log", out / "capture.json") if p.exists())
for name in ("CLOUDFLARE_AI_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_WORKER_TOKEN", "OPENAI_API_KEY", "RAILWAY_TOKEN"):
    value = os.environ.get(name, "").strip()
    if value and value in text:
        print(f"FAIL: {name} leaked into outputs"); sys.exit(1)
print("no credential in outputs")
PY
) || exit 1
