"""Fail unless a fresh baseline run matches the frozen T1 evidence (ignoring the dirty flag)."""

import json
import sys
from pathlib import Path

frozen, fresh = (json.loads(Path(path).read_text()) for path in sys.argv[1:3])
for payload in (frozen, fresh):
    payload["source"].pop("dirty", None)
    payload["source"].pop("package_hash", None)
if frozen["cases"] != fresh["cases"]:
    for old, new in zip(frozen["cases"], fresh["cases"], strict=True):
        if old != new:
            keys = [key for key in old if old[key] != new.get(key)]
            print(f"case {old['id']} changed: {keys}")
    sys.exit(1)
print("baseline cases identical:", len(fresh["cases"]))
