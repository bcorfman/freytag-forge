# ruff: noqa: E501
"""Write the Ringer runner manifest for the two billed drain-rejection probes (P2 replay, P3 screen)."""

import json
from pathlib import Path

ROOT = "/home/bcorfman/dev/freytag-forge"
ED = "scripts/ringer/environment_narration"
OUT = "bench/results/environment-narration"

RUNS = [
    {
        "key": "billed-replay",
        "wrapper": "enforce_t9h_drain_replay.sh replay",
        "rows": f"{OUT}/t9h-drain-replay/rows.json",
        "calls": 60,
        "usd": "0.005",
        "desc": "60 Jev relation requests (6 frozen cases x V0/J1c x 5 samples), ceiling about $0.0012",
        "prereg": ".plans/grounded-llm-environment-narration/t9h-drain-replay-prereg.md",
    },
    {
        "key": "billed-screen",
        "wrapper": "enforce_t9h_drain_details.sh screen",
        "rows": f"{OUT}/t9h-drain-details/screen/rows.json",
        "calls": 20,
        "usd": "0.03",
        "desc": "20 narration requests (the recorded drain prompt, control vs one Details-line addition, 10 samples each), ceiling about $0.014",
        "prereg": ".plans/grounded-llm-environment-narration/t9h-drain-details-prereg.md",
    },
]


def check(run: dict) -> str:
    return (
        f"cd {ROOT} && export PYTHONPATH={ROOT} && set -o pipefail && test -s {run['rows']} && "
        f"(set -a; . ./.env; set +a; .venv/bin/python - <<'PY2'\n"
        "import json,os\n"
        f"p='{run['rows']}'\n"
        "doc=json.load(open(p))\n"
        "rows=doc['rows'] if isinstance(doc,dict) and 'rows' in doc else doc\n"
        "text=open(p).read()\n"
        "for n in ('CLOUDFLARE_AI_TOKEN','CLOUDFLARE_ACCOUNT_ID','CLOUDFLARE_WORKER_TOKEN','OPENAI_API_KEY','RAILWAY_TOKEN'):\n"
        "    v=os.environ.get(n,'').strip()\n"
        "    assert not v or v not in text, n+' leaked'\n"
        f"planned={run['calls']}\n"
        "stop=doc.get('stop_reason') if isinstance(doc,dict) else None\n"
        "assert len(rows)==planned or stop, 'incomplete run without a stop reason: %d rows'%len(rows)\n"
        "print('integrity ok: %d rows, stop_reason %r, no credential in outputs'%(len(rows),stop))\n"
        "PY2\n)"
    )


def task(run: dict) -> dict:
    spec = (
        f"You are a RUNNER for one billed probe in freytag-forge. Working directory: {ROOT}. It sends {run['desc']}, "
        f"through the project's local Worker, hard-capped at {run['calls']} calls and ${run['usd']}. The user approved "
        f"this run on 2026-10-30; the preregistration is {run['prereg']}. HARD RULES: run COMMAND 1 EXACTLY ONCE in the "
        "FOREGROUND and never rerun it, even after an error or partial result (a rerun would spend money again). Do not "
        "edit any file. Do not print, echo, cat or log environment variables or the .env file or any credential. Do not "
        "git commit. A non-zero exit with partial rows is a valid outcome. Wait for the billed process to finish.\n\n"
        "COMMAND 1 (the billed run; run exactly once):\n"
        f"cd {ROOT} && (set -a; . ./.env; set +a; unset OPENAI_API_KEY RAILWAY_TOKEN RAILWAY_PROJECT_ID "
        f"FREYTAG_TEST_CLOCK_TOKEN; bash {ED}/{run['wrapper']})\n\n"
        "Then report only the probe's non-secret output, including any stop reason. Do not interpret quality."
    )
    return {
        "key": run["key"],
        "task_type": "probe",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=low"],
        "full_access": True,
        "max_attempts": 1,
        "timeout_s": 3600,
        "check_timeout_s": 300,
        "ownership": [f"{ROOT}/{run['rows']}"],
        "expect_files": [f"{ROOT}/{run['rows']}"],
        "verified": "rows recorded (all planned calls or a stop reason), no credential in outputs",
        "spec": spec,
        "check": check(run),
    }


manifest = {
    "run_name": "t9h-drain-rejection-p1-p3",
    "workdir": "/home/bcorfman/dev/ringer-work/t9h-drain-rejection-p1-p3",
    "max_parallel": 2,
    "worktrees": False,
    "repo": ROOT,
    "tasks": [task(run) for run in RUNS],
}
out = Path(__file__).with_name("run-t9h-drain-rejection-billed.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
