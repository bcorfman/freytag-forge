# ruff: noqa: E501
"""Generate the Ringer manifest for the billed stage 2 run of the narration-defect probe."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/run-defect-probe-s2.json"
B = "bench/results/environment-narration"
ROWS, SHEET, KEY = f"{B}/defect-probe-s2-rows.json", f"{B}/defect-probe-s2-sheet.md", f"{B}/defect-probe-s2-key.json"
PY = "scripts/ringer/environment_narration/defect_probe.py"

SPEC = (
    "You are a RUNNER for one billed probe in freytag-forge. Working directory: /home/bcorfman/dev/freytag-forge. It is STAGE 2 of the preregistered probe: 60 narration requests to Cloudflare Workers AI (70B; arms A1 and B2 and their controls A0 and B0, 15 samples each, samples 10 to 24). The actual-spend cap is $0.08 and the human approved the run. HARD RULES: run COMMAND 1 EXACTLY ONCE. NEVER run it a second time for any reason. COMMAND 1 TAKES ABOUT 2 TO 4 MINUTES. Your shell tool may return before it has exited; if it says the process is still running, KEEP WAITING AND POLLING THAT SAME SESSION until it exits. Do NOT end your task, run COMMAND 2 or give your final answer until COMMAND 1 has exited (the previous attempt was killed because the task ended early). Do not edit any file. Do not print, echo, cat or log environment variables or the .env file or any credential. Do not git commit. "
    "NEVER open, cat, print or summarize the key file (defect-probe-s2-key.json) or the sheet: the orchestrator must read replies blind to arm. Only print the lines the commands themselves print.\n\n"
    f"COMMAND 1 (the billed stage 2 run; a non-zero exit with partial rows is a valid outcome, do not retry):\ncd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && (set -a; . ./.env; set +a; unset OPENAI_API_KEY RAILWAY_TOKEN RAILWAY_PROJECT_ID FREYTAG_TEST_CLOCK_TOKEN; .venv/bin/python {PY} --run --confirm --stage 2 --arms A1,B2 --max-calls 60 --max-usd 0.08 --out {ROWS})\n\n"
    f"COMMAND 2 (renders the blind sheet and key; safe to rerun if it fails):\ncd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && .venv/bin/python {PY} --sheet --rows {ROWS} --out {SHEET} --key {KEY}\n\n"
    "COMMAND 3: print only the number of rows and the stop_reason from the rows file with this exact one-liner: "
    f".venv/bin/python -c \"import json;d=json.load(open('{ROWS}'));print(len(d['rows']),d.get('stop_reason'),round(sum(r.get('actual_cost_usd') or 0 for r in d['rows']),5))\"\n"
    "Then say in one or two sentences what happened (row count, stop reason, cost, the key file SHA-256 line COMMAND 2 printed). Do not interpret the replies."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge && set -o pipefail && "
    f"test -s {ROWS} && test -s {SHEET} && test -s {KEY} && (set -a; . ./.env; set +a; .venv/bin/python - <<'PY2'\n"
    "import json,os\n"
    f"d=json.load(open('{ROWS}'))\n"
    f"text=open('{ROWS}').read()+open('{SHEET}').read()+open('{KEY}').read()\n"
    "for n in ('CLOUDFLARE_AI_TOKEN','CLOUDFLARE_ACCOUNT_ID','CF_API_TOKEN','CLOUDFLARE_WORKER_TOKEN','OPENAI_API_KEY','RAILWAY_TOKEN'):\n"
    "    v=os.environ.get(n,'').strip()\n"
    "    assert not v or v not in text, n+' leaked'\n"
    "assert d.get('complete') is True and len(d['rows'])==60, 'incomplete: %s rows, stop_reason %s'%(len(d['rows']),d.get('stop_reason'))\n"
    "sheet=open('" + SHEET + "').read()\n"
    "for arm in ('A0','A1','A2','A3','B0','B1','B2','B3'):\n"
    "    assert arm not in sheet.replace('Defect A','').replace('Defect B',''), 'arm id in sheet: '+arm\n"
    "print('integrity ok: %d rows, no credential in outputs, no arm id in sheet'%len(d['rows']))\n"
    "PY2\n)"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-defect-s2",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "billed-defect-probe-stage2",
            "task_type": "probe",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "full_access": True,
            "max_attempts": 1,
            "timeout_s": 2400,
            "check_timeout_s": 300,
            "ownership": [ROWS, SHEET, KEY],
            "expect_files": [f"{REPO}/{ROWS}", f"{REPO}/{SHEET}", f"{REPO}/{KEY}"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "rows recorded, blind sheet and key rendered, no credential in outputs, no arm id on the sheet",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
