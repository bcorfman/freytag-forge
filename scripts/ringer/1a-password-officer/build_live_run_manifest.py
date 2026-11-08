# ruff: noqa: E501
"""Build a one-task Ringer manifest whose CHECK performs the billed live greeting run.
Usage: .venv/bin/python scripts/ringer/1a-password-officer/build_live_run_manifest.py smoke|run"""

import json
import sys
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
OUT = f"{R}/bench/results/1a-password-officer"
tag = sys.argv[1]
assert tag in {"smoke", "run"}
samples, cap = (1, 4) if tag == "smoke" else (12, 32)
name = f"{tag}-live"
rows, ready, log = f"{OUT}/{name}-rows.json", f"{OUT}/{name}-ready.txt", f"{OUT}/{name}.log"
check = f"""set -eo pipefail
cd {R}
export PYTHONPATH={R}:{R}/packages/worldkeeper/src TMPDIR=/tmp
[ ! -e {rows} ] || {{ echo 'rows file already exists; refusing to re-bill'; exit 1; }}
{R}/.venv/bin/python {D}/live_greeting.py {rows} {samples} --confirm --cap {cap} > {log} 2>&1 || {{ tail -20 {log}; echo 'live run failed'; exit 1; }}
{R}/.venv/bin/python - <<'PY'
import json
rows = json.load(open('{rows}'))
req = sum(r['requests'] for r in rows)
err = [(r['arm'], r['sample'], (r['error'] or '')[:80]) for r in rows if r['error']]
print('turns', len(rows), 'real requests', req, 'cap', {cap}, 'errors', len(err), err)
assert rows and req <= {cap}
PY
"""
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
    "spec": f"You are a trivial placeholder worker for a billed run that Ringer's check performs itself. Boundary: do NOT run any harness, do NOT call any model or network service, do NOT touch any file except the one you own, never git commit. Your only job: write the single line 'ready {name}' into the file {ready} (create it; the directory exists). Nothing else is needed; the check afterwards runs {samples} sample(s) of the live greeting check (.plans/1a-password-officer-prereg.md) with a hard cap of {cap} real requests and writes {rows}. Do not read or edit anything else.",
    "check": check,
    "verified": "the live harness wrote its rows within the request cap (errors kept as rows)",
}
manifest = {
    "run_name": f"live-greeting-check-{name}",
    "workdir": f"/home/bcorfman/dev/ringer-work/live-greeting-check-{name}",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
path = Path(D) / f"{name}-manifest.json"
path.write_text(json.dumps(manifest, indent=2) + "\n")
print(path)
