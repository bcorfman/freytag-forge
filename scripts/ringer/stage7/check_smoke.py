"""usage: check_smoke.py ATTEMPT_DIR -- a smoke counts as recorded if it holds staging identity for the
expected SHA, a smoke-result.txt saying passed or failed, and an operator note."""

import json
import sys
from pathlib import Path

EXPECTED_SHA = "f918c663d67d368645f9a24a47a28ffb29fb77d8"
d = Path(sys.argv[1])
errs = []
try:
    v = json.loads((d / "identity.json").read_text())
    if v.get("channel") != "staging" or v.get("runtime") != "scene-v1":
        errs.append(f"identity not staging/scene-v1: {v}")
    if v.get("sha") != EXPECTED_SHA:
        errs.append(f"identity sha {v.get('sha')} != {EXPECTED_SHA}")
except Exception as e:
    errs.append(f"identity.json unreadable: {e}")
result = d / "smoke-result.txt"
if not result.is_file() or result.read_text().split()[:1] not in (["passed"], ["failed"], ["not"]):
    errs.append("smoke-result.txt missing or does not start with passed, failed or not run")
note = d / "operator-note.md"
if not note.is_file() or note.stat().st_size < 100:
    errs.append("operator-note.md missing or too short")
if errs:
    print("\n".join(errs))
    sys.exit(1)
print("smoke recorded")
