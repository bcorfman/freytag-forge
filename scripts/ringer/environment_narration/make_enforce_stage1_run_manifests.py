"""Generate the Ringer manifests for the T9 enforcing-verifier stage 1 run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path("/home/bcorfman/dev/freytag-forge")
HERE = Path(__file__).resolve().parent
PREREG = ".plans/grounded-llm-environment-narration/t9-enforce-stage1-prereg.md"
ROUTE = (
    "inspect the drawer, pull out the drawer, feel under the drawer, feel under the drawer, "
    "go outside, inspect the truck, enter the truck, pick up my laptop, inspect the passenger seat"
)


def _spec(stage: str, calls: int, ceiling: str) -> str:
    return (
        f"You are a RUNNER for one billed T9 stage-1 enforcing-verifier sample ({stage} stage) in freytag-forge. "
        "Working directory: /home/bcorfman/dev/freytag-forge. It plays the `observe_topup` route (9 commands): "
        f"{ROUTE} through the real product path against a LOCAL Worker on 127.0.0.1 with the enforcing observation "
        f"verifier ON. This stage is approved in the preregistration {PREREG}. It uses a cap of {calls} calls and "
        f"a ceiling of ${ceiling}. HARD RULES: run COMMAND 1 EXACTLY ONCE. NEVER run it a second time for any "
        "reason (not after an error, not after a partial result: a rerun spends money again). Do not edit any file. "
        "Do not print, echo, cat or log environment variables or the .env file or any credential. Do not git commit. "
        "Run COMMAND 1 in the FOREGROUND and wait for it to exit; do not finish while the script is running. The "
        "script refuses to run if its port is busy; do not do your own port checks, just run COMMAND 1 once.\n\n"
        "COMMAND 1 (the billed run; a non-zero exit with partial rows is a valid outcome, do not retry):\n"
        "cd /home/bcorfman/dev/freytag-forge && bash "
        f"scripts/ringer/environment_narration/enforce_stage1.sh {stage}\n\n"
        "The script starts the local Worker, runs the frozen route, writes rows.json and summary.json under "
        f"bench/results/environment-narration/enforce-stage1/{stage}/rows, writes "
        f"bench/results/environment-narration/enforce-stage1/{stage}/spent.json, and stops the Worker. "
        "Report the exit code, the lines the script printed (they contain no secrets), and the contents of "
        "spent.json. Do not interpret the results beyond that."
    )


def _check(stage: str, replicates: int, ceiling_micro_usd: int) -> str:
    base = f"bench/results/environment-narration/enforce-stage1/{stage}"
    route_check = ""
    if stage == "smoke":
        route_check = "assert len(rows) == 1, 'unexpected replicate count'"
    else:
        route_check = "assert len(rows) == 10, 'unexpected replicate count'"
    return (
        "cd /home/bcorfman/dev/freytag-forge && set -o pipefail && "
        f"test -f {base}/rows/rows.json && test -f {base}/rows/summary.json && test -f {base}/spent.json && "
        ".venv/bin/python - <<'PY'\n"
        "import json\n"
        f"base={base!r}\n"
        "rows=json.load(open(base+'/rows/rows.json'))\n"
        "summary=json.load(open(base+'/rows/summary.json'))\n"
        "assert summary['enforce'] is True, 'enforce not on'\n"
        "assert summary.get('shadow', False) is False, 'shadow on'\n"
        "spent=json.load(open(base+'/spent.json'))\n"
        f"assert spent['spent_micro_usd'] <= {ceiling_micro_usd}, 'cap exceeded'\n"
        "for row in rows:\n"
        "    for turn in row.get('turns', []):\n"
        "        assert 'turn_elapsed_s' in turn\n"
        "        assert 'enforce_attempts' in turn\n"
        "        assert 'narration_attempts' in turn\n"
        "if summary.get('stopped_reason') is None:\n"
        f"    {route_check}\n"
        "    assert all(len(row.get('turns', [])) == 9 for row in rows), 'incomplete route'\n"
        "    for row in rows:\n"
        "        assert row['turns'][7]['input'] == 'pick up my laptop', 'wrong eighth command'\n"
        "        assert row['turns'][-1]['input'] == 'inspect the passenger seat', 'wrong final command'\n"
        "print('replicates',len(rows),'turns',sum(len(r.get('turns',[])) for r in rows),"
        "'stopped',summary.get('stopped_reason'))\n"
        "print('spent',spent)\n"
        "PY\n"
        "(set -a; . ./.env; set +a; .venv/bin/python - <<'PY'\n"
        "import os\n"
        f"base={base!r}\n"
        "text=''.join(open(os.path.join(directory, filename)).read() for directory, _, filenames in os.walk(base) "
        "for filename in filenames)\n"
        "for name in ('CLOUDFLARE_AI_TOKEN','CLOUDFLARE_ACCOUNT_ID','CLOUDFLARE_WORKER_TOKEN'):\n"
        "    value=os.environ.get(name,'').strip()\n"
        "    assert not value or value not in text, name+' value leaked into outputs'\n"
        "print('no credential in outputs')\n"
        "PY\n"
        ")"
    )


def _manifest(stage: str) -> dict[str, Any]:
    settings = {
        "smoke": (1, 70, "0.03", 30000),
        "full": (10, 700, "0.20", 200000),
    }
    replicates, calls, ceiling, ceiling_micro_usd = settings[stage]
    base = f"bench/results/environment-narration/enforce-stage1/{stage}"
    task = {
        "key": f"billed-enforce-stage1-{stage}",
        "task_type": "probe",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=low"],
        "full_access": True,
        "max_attempts": 1,
        "timeout_s": 3600,
        "check_timeout_s": 300,
        "ownership": [base],
        "expect_files": [
            f"{REPO}/{base}/rows/rows.json",
            f"{REPO}/{base}/rows/summary.json",
            f"{REPO}/{base}/spent.json",
        ],
        "spec": _spec(stage, calls, ceiling),
        "check": _check(stage, replicates, ceiling_micro_usd),
        "verified": "one enforcing-verifier stage-1 sample ran once under the approved cap",
    }
    return {
        "run_name": "grounded-environment-narration",
        "workdir": f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-enforce-stage1-{stage}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": str(REPO),
        "tasks": [task],
    }


def main(output_dir: Path | None = None) -> None:
    destination = HERE if output_dir is None else output_dir
    destination.mkdir(parents=True, exist_ok=True)
    for stage in ("smoke", "full"):
        target = destination / f"run-enforce-stage1-{stage}.json"
        target.write_text(json.dumps(_manifest(stage), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
