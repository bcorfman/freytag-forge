"""usage: check_attempt.py REPO ATTEMPT_DIR  -- an attempt counts as recorded if it holds a fresh spine report or a verbatim failure."""
import json, sys
from pathlib import Path

repo, d = Path(sys.argv[1]), Path(sys.argv[2])
errs = []
note = d / "operator-note.md"
if not note.is_file() or note.stat().st_size < 200:
    errs.append("operator-note.md missing or too short")
ident = d / "identity.json"
try:
    v = json.loads(ident.read_text())
    if v.get("channel") != "staging" or v.get("runtime") != "scene-v1":
        errs.append(f"identity not staging/scene-v1: {v}")
    if not v.get("sha"):
        errs.append("identity has no sha")
except Exception as e:
    errs.append(f"identity.json unreadable: {e}")
rep = d / "e2e-spine.json"
fail = d / "run-failure.txt"
if rep.is_file():
    try:
        r = json.loads(rep.read_text())
        for k in ("chains", "story_complete", "attempt", "identity", "latency", "per_turn"):
            if k not in r:
                errs.append(f"report lacks {k} (stale or pre-change report?)")
        if r.get("identity", {}).get("sha") != json.loads(ident.read_text()).get("sha"):
            errs.append("report identity sha differs from identity.json")
        if not r.get("per_turn"):
            errs.append("report has zero turns")
    except Exception as e:
        errs.append(f"report unreadable: {e}")
elif fail.is_file() and fail.stat().st_size > 20:
    pass
else:
    errs.append("neither e2e-spine.json nor a non-empty run-failure.txt")
if errs:
    print("\n".join(errs)); sys.exit(1)
print("attempt recorded")
