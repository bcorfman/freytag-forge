# ruff: noqa: E501
"""Build a one-task Ringer manifest whose CHECK performs one billed 1A replay (the worker only writes a ready file).
Usage: .venv/bin/python scripts/ringer/1a-password-officer/build_run_manifest.py STAGE FIRST LAST TAG   (TAG: smoke or run)"""

import json
import sys
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
OUT = f"{R}/bench/results/1a-password-officer"
CELLS = {"officer": 4, "walt": 2, "password": 3, "voice": 4, "recovery": 1}
stage, first, last, tag = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
assert stage in CELLS and 0 <= first <= last <= 12 and tag in {"smoke", "run"}
name = f"{tag}-{stage}"
rows, ready, log = f"{OUT}/{name}-rows.json", f"{OUT}/{name}-ready.txt", f"{OUT}/{name}.log"
expected = CELLS[stage] * (last - first + 1)
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
    "spec": f"You are a trivial placeholder worker for a billed replay that Ringer's check performs itself. Boundary: do NOT run any replay, do NOT call any model or network service, do NOT touch any file except the one you own, never git commit. Your only job: write the single line 'ready {name}' into the file {ready} (create it; the directory exists). Nothing else is needed; the check afterwards replays samples {first} to {last} of the 1A {stage} stage (.plans/1a-password-officer-prereg.md) and writes {rows}. Do not read or edit anything else.",
    "check": f"set -o pipefail\ncd {R}\nexport PYTHONPATH={R}:{R}/packages/worldkeeper/src TMPDIR=/tmp\n[ ! -e {rows} ] || {{ echo 'rows file already exists; refusing to re-bill'; exit 1; }}\n{R}/.venv/bin/python {D}/replay.py {stage} {rows} {first} {last} --confirm > {log} 2>&1; code=$?\ntail -5 {log}\n[ $code -eq 0 ] || {{ echo \"replay exited $code\"; exit $code; }}\n{R}/.venv/bin/python - <<'PY'\nimport json,sys\nr=json.load(open('{rows}'))\nerrs=[(x['arm'],x['n'],x['sample'],x['error'][:80]) for x in r if x.get('error')]\nprint('rows',len(r),'errors',len(errs),errs)\nsys.exit(0 if len(r)=={expected} else 'expected {expected} rows, got %d'%len(r))\nPY\n",
    "verified": "the replay wrote every row (errors kept as rows)",
}
manifest = {
    "run_name": f"1a-password-officer-{name}",
    "workdir": f"/home/bcorfman/dev/ringer-work/1a-password-officer-{name}",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
path = Path(D) / f"{name}-manifest.json"
path.write_text(json.dumps(manifest, indent=2) + "\n")
print(path)
