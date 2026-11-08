# ruff: noqa: E501
"""Amendment 19 billed probe manifest: three placeholder-worker tasks whose checks run the interleaved replay."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
LOC = f"{REPO}/bench/results/richer-3a-probe/speech"
PY = f"{REPO}/.venv/bin/python"
tasks = []
for key, first, last in (("sp-1-4", 1, 4), ("sp-5-8", 5, 8), ("sp-9-12", 9, 12)):
    ready = f"{LOC}/{key}-ready.txt"
    rows = f"{LOC}/{key}-rows.json"
    tasks.append(
        {
            "key": key,
            "task_type": "probe",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 1,
            "timeout_s": 300,
            "check_timeout_s": 3000,
            "ownership": [ready],
            "expect_files": [ready],
            "spec": f"You are a trivial placeholder worker for a billed replay that Ringer's check performs itself. Boundary: do NOT run any replay, do NOT call any model or network service, do NOT touch any file except the one you own, never git commit. Your only job: write the single line 'ready {key}' into the file {ready} (create it; the directory exists). Nothing else is needed; the check afterwards replays samples {first} to {last} of the frozen C/S payloads (Amendment 20 of .plans/richer-3a-probe-prereg.md) and writes {rows}. Do not read or edit anything else.",
            "check": f"""set -o pipefail
cd {REPO}
export PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src TMPDIR=/tmp
[ ! -e {rows} ] || {{ echo 'rows file already exists; refusing to re-bill'; exit 1; }}
{PY} scripts/ringer/3a-open-issues/speech_replay.py {rows} {first} {last} 2>&1 | tee {LOC}/{key}.log | tail -5
{PY} - <<'PY'
import json,sys
r=json.load(open('{rows}'))
errs=[(x['arm'],x['n'],x['sample']) for x in r if x.get('error')]
print('rows',len(r),'errors',len(errs),errs)
sys.exit(0 if len(r)=={(last - first + 1) * 6} else 'expected {(last - first + 1) * 6} rows, got %d'%len(r))
PY
""",
            "verified": "the replay wrote every row (errors kept as rows)",
        }
    )
manifest = {
    "run_name": "3a-speech-probe",
    "workdir": "/home/bcorfman/dev/ringer-work/3a-speech-probe",
    "max_parallel": 3,
    "worktrees": False,
    "repo": REPO,
    "tasks": tasks,
}
Path(__file__).with_name("speech-probe-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
