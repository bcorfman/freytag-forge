"""usage: check_alias_attempt.py REPO ATTEMPT_DIR -- an @alias-smoke attempt counts if recorded with
staging identity and a fresh report or verbatim failure.
"""

import json
import sys
from pathlib import Path

d = Path(sys.argv[2])
errs = []
note = d / "operator-note.md"
if not note.is_file() or note.stat().st_size < 150:
    errs.append("operator-note.md missing or too short")
sha = None
try:
    v = json.loads((d / "identity.json").read_text())
    sha = v.get("sha")
    if v.get("channel") != "staging" or v.get("runtime") != "scene-v1" or not sha:
        errs.append(f"identity not staging/scene-v1 with sha: {v}")
except Exception as e:
    errs.append(f"identity.json unreadable: {e}")
rep, fail = d / "e2e-alias-smoke.json", d / "run-failure.txt"
if rep.is_file():
    try:
        r = json.loads(rep.read_text())
        for k in ("identity", "summary", "photo_turns", "one_b_turns", "bundles_visible"):
            if k not in r:
                errs.append(f"report lacks {k}")
        if r.get("identity", {}).get("sha") != sha:
            errs.append("report identity sha differs from identity.json")
        if not r.get("photo_turns"):
            errs.append("report has no photo turns")
    except Exception as e:
        errs.append(f"report unreadable: {e}")
elif not (fail.is_file() and fail.stat().st_size > 20):
    errs.append("neither e2e-alias-smoke.json nor a non-empty run-failure.txt")
if errs:
    print("\n".join(errs))
    sys.exit(1)
print("attempt recorded")
