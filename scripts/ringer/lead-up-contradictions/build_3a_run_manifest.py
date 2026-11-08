# ruff: noqa: E501
"""Build a one-task Ringer manifest that runs the billed 3A replay as the task's CHECK (the worker only writes a ready file).
Usage: .venv/bin/python scripts/ringer/lead-up-contradictions/build_3a_run_manifest.py FIRST LAST TAG   (TAG is 'smoke' or 'run')"""

import json
import sys
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
first, last, tag = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
name = f"{tag}-3A"
out = f"{R}/bench/results/lead-up-contradictions"
rows, ready, log = f"{out}/{name}-rows.json", f"{out}/{name}-ready.txt", f"{out}/{name}.log"
expected = (last - first + 1) * 4
task = {
    "key": name,
    "task_type": "probe",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=low"],
    "max_attempts": 1,
    "timeout_s": 300,
    "check_timeout_s": 3000,
    "ownership": [ready],
    "expect_files": [ready],
    "spec": f"You are a trivial placeholder worker for a billed replay that Ringer's check performs itself. Boundary: do NOT run any replay, do NOT call any model or network service, do NOT touch any file except the one you own, never git commit. Your only job: write the single line 'ready {name}' into the file {ready} (create it; the directory exists). Nothing else is needed; the check afterwards replays samples {first} to {last} of comparison 3A (current vs candidate reunion delivery at R1 and R2, .plans/lead-up-contradictions-prereg.md) and writes {rows}. Do not read or edit anything else.",
    "check": f"set -o pipefail\ncd {R}\nexport PYTHONPATH={R}:{R}/packages/worldkeeper/src TMPDIR=/tmp\n[ ! -e {rows} ] || {{ echo 'rows file already exists; refusing to re-bill'; exit 1; }}\n{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/replay_3a.py {rows} {first} {last} --confirm 2>&1 | tee {log} | tail -5\n{R}/.venv/bin/python - <<'PY'\nimport json,sys\nr=json.load(open('{rows}'))\nerrs=[(x['arm'],x['n'],x['sample']) for x in r if x.get('error')]\nprint('rows',len(r),'errors',len(errs),errs)\nsys.exit(0 if len(r)=={expected} else 'expected {expected} rows, got %d'%len(r))\nPY\n",
    "verified": "the replay wrote every row (errors kept as rows)",
}
manifest = {
    "run_name": f"lead-up-contradictions-{name}",
    "workdir": f"/home/bcorfman/dev/ringer-work/lead-up-contradictions-{name}",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
path = Path(R) / f"scripts/ringer/lead-up-contradictions/{name}-manifest.json"
path.write_text(json.dumps(manifest, indent=2) + "\n")
print(path)
