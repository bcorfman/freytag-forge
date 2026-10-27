"""Generate the Ringer manifests for the T9b enforced runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path("/home/bcorfman/dev/freytag-forge")
HERE = Path(__file__).resolve().parent
PREREG = ".plans/grounded-llm-environment-narration/t9b-scope-prereg.md"
ROUTE_A = (
    "inspect the drawer, pull out the drawer, feel under the drawer, feel under the drawer, "
    "go outside, inspect the truck, enter the truck, pick up my laptop, inspect the passenger seat"
)
ROUTE_B = "feel under the drawer, feel under the drawer, inspect the drawer, pull out the drawer"


def _spec(stage: str, replicates_a: int, calls_a: int, replicates_b: int, calls_b: int, ceiling: str) -> str:
    return (
        f"You are a RUNNER for one billed T9b scope-aware observation contract sample ({stage} stage) in "
        "freytag-forge. Working directory: /home/bcorfman/dev/freytag-forge. It runs route A "
        f"`observe_topup` ({ROUTE_A}) and then route B `observe_under_first` ({ROUTE_B}) through the real "
        "product path against a LOCAL Worker on 127.0.0.1 with the enforcing observation verifier ON and shadow "
        f"off. This stage is approved in the preregistration {PREREG}. Route A uses --replicates {replicates_a} "
        f"--max-calls {calls_a}; route B uses --replicates {replicates_b} --max-calls {calls_b}; the "
        f"Worker ceiling is ${ceiling}. HARD RULES: run COMMAND 1 EXACTLY ONCE. NEVER run it a second time for "
        "any reason (not after an error, not after a partial result: a rerun spends money again). Do not edit any "
        "file. Do not print, echo, cat or log environment variables or the .env file or any credential. Do not git "
        "commit. Run COMMAND 1 in the FOREGROUND and wait for it to exit; do not finish while the script is running. "
        "The script refuses to run if its port is busy; do not do your own port checks, just run COMMAND 1 once.\n\n"
        "COMMAND 1 (the billed run; a non-zero exit with partial rows is a valid outcome, do not retry):\n"
        f"cd /home/bcorfman/dev/freytag-forge && bash "
        f"scripts/ringer/environment_narration/enforce_stage2.sh {stage}\n\n"
        "The script starts one local Worker, runs A and then B when A has no stop reason, writes rows.json and "
        f"summary.json under bench/results/environment-narration/t9b-scope/{stage}/a/rows and "
        f".../{stage}/b/rows, writes bench/results/environment-narration/t9b-scope/{stage}/spent.json, and stops "
        "the Worker. Report the exit codes, the lines the script printed (they contain no secrets), and the contents "
        "of spent.json. Do not interpret the results beyond that."
    )


def _check(stage: str, ceiling_micro_usd: int, replicates_a: int, replicates_b: int) -> str:
    base = f"bench/results/environment-narration/t9b-scope/{stage}"
    return (
        "cd /home/bcorfman/dev/freytag-forge && set -o pipefail && "
        f"test -f {base}/a/rows/rows.json && test -f {base}/a/rows/summary.json && "
        f"test -f {base}/spent.json && .venv/bin/python - <<'PY'\n"
        "import json\n"
        "import os\n"
        "from pathlib import Path\n\n"
        f"base = Path({base!r})\n"
        "spent = json.loads((base / 'spent.json').read_text())\n"
        f"assert spent['spent_micro_usd'] <= {ceiling_micro_usd}, 'cap exceeded'\n"
        "def route_rows(name, expected_replicates, expected_turns, last_input):\n"
        "    route_base = base / name / 'rows'\n"
        "    rows = json.loads((route_base / 'rows.json').read_text())\n"
        "    summary = json.loads((route_base / 'summary.json').read_text())\n"
        "    assert summary['enforce'] is True, 'enforce not on'\n"
        "    assert summary.get('shadow', False) is False, 'shadow on'\n"
        "    for row in rows:\n"
        "        for turn in row.get('turns', []):\n"
        "            assert 'turn_elapsed_s' in turn\n"
        "            assert 'enforce_attempts' in turn\n"
        "            assert 'narration_attempts' in turn\n"
        "            assert 'observation_request' in turn\n"
        "    if summary.get('stopped_reason') is None:\n"
        "        assert len(rows) == expected_replicates, 'unexpected replicate count'\n"
        "        assert all(len(row.get('turns', [])) == expected_turns for row in rows), 'incomplete route'\n"
        "        assert all(row['turns'][-1]['input'] == last_input for row in rows)\n"
        "        if name == 'a':\n"
        "            assert all(row['turns'][7]['input'] == 'pick up my laptop' for row in rows)\n"
        "route_rows('a', "
        f"{replicates_a}, 9, 'inspect the passenger seat')\n"
        "a_summary = json.loads((base / 'a' / 'rows' / 'summary.json').read_text())\n"
        "if a_summary.get('stopped_reason') is None:\n"
        "    assert (base / 'b' / 'rows' / 'rows.json').is_file()\n"
        "    assert (base / 'b' / 'rows' / 'summary.json').is_file()\n"
        f"    route_rows('b', {replicates_b}, 4, 'pull out the drawer')\n"
        "print('checked routes and spent cap')\n"
        "PY\n"
        "(set -a; . ./.env; set +a; .venv/bin/python - <<'PY'\n"
        "import os\n"
        "from pathlib import Path\n\n"
        f"base = Path({base!r})\n"
        "text = ''.join(path.read_text(errors='replace') for path in base.rglob('*') if path.is_file())\n"
        "for name in ('CLOUDFLARE_AI_TOKEN', 'CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_WORKER_TOKEN'):\n"
        "    value = os.environ.get(name, '').strip()\n"
        "    assert not value or value not in text, name + ' value leaked into outputs'\n"
        "print('no credential in outputs')\n"
        "PY\n"
        ")"
    )


def _manifest(stage: str) -> dict[str, Any]:
    settings = {
        "smoke": (1, 90, 1, 40, "0.05", 50000),
        "full": (10, 800, 5, 250, "0.30", 300000),
    }
    replicates_a, calls_a, replicates_b, calls_b, ceiling, ceiling_micro_usd = settings[stage]
    base = f"bench/results/environment-narration/t9b-scope/{stage}"
    task = {
        "key": f"billed-t9b-{stage}",
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
            f"{REPO}/{base}/a/rows/rows.json",
            f"{REPO}/{base}/a/rows/summary.json",
            f"{REPO}/{base}/b/rows/rows.json",
            f"{REPO}/{base}/b/rows/summary.json",
            f"{REPO}/{base}/spent.json",
        ],
        "spec": _spec(stage, replicates_a, calls_a, replicates_b, calls_b, ceiling),
        "check": _check(stage, ceiling_micro_usd, replicates_a, replicates_b),
        "verified": "the T9b two-route enforcing-verifier sample ran once under the approved cap",
    }
    return {
        "run_name": "grounded-environment-narration",
        "workdir": f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9b-{stage}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": str(REPO),
        "tasks": [task],
    }


def main(output_dir: Path | None = None) -> None:
    destination = HERE if output_dir is None else output_dir
    destination.mkdir(parents=True, exist_ok=True)
    for stage in ("smoke", "full"):
        target = destination / f"run-t9b-{stage}.json"
        target.write_text(json.dumps(_manifest(stage), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
