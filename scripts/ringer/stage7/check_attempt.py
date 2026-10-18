"""usage: check_attempt.py ATTEMPT_DIR -- an attempt counts as recorded if it holds identity, smoke result,
a fresh blind-player report or a verbatim failure, and an operator note."""

import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
errs = []
note = d / "operator-note.md"
if not note.is_file() or note.stat().st_size < 200:
    errs.append("operator-note.md missing or too short")
try:
    v = json.loads((d / "identity.json").read_text())
    if v.get("channel") != "staging" or v.get("runtime") != "scene-v1":
        errs.append(f"identity not staging/scene-v1: {v}")
    if not v.get("sha"):
        errs.append("identity has no sha")
except Exception as e:
    errs.append(f"identity.json unreadable: {e}")
if not (d / "smoke-result.txt").is_file():
    errs.append("smoke-result.txt missing")
rep = d / "e2e-blind-player-r1.json"
if not rep.is_file():
    rep = d / "e2e-blind-player.json"  # single-replicate runs write the unsuffixed name
fail = d / "run-failure.txt"
if rep.is_file():
    try:
        r = json.loads(rep.read_text())
        if not r:
            errs.append("report is empty")
    except Exception as e:
        errs.append(f"report unreadable: {e}")
elif not (fail.is_file() and fail.stat().st_size > 20):
    errs.append("neither e2e-blind-player(-r1).json nor a non-empty run-failure.txt")
if errs:
    print("\n".join(errs))
    sys.exit(1)
print("attempt recorded")
