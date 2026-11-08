"""Print {path: sha256} for every tracked or untracked-not-ignored file under the repo root (run from the repo root).
Used by Ringer checks that run in a dirty tree: compare against a snapshot taken before the worker started."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

files = subprocess.run(
    ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"], capture_output=True, check=True
).stdout.split(b"\0")
out = {}
for raw in files:
    if not raw:
        continue
    path = Path(raw.decode())
    if path.is_file() and not path.is_symlink() and not str(path).startswith(".venv"):
        out[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
Path(sys.argv[1]).write_text(json.dumps(out, indent=0, sort_keys=True))
print(len(out), "files")
