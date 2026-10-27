"""Generate the Ringer manifest for the billed T9b second Jev probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path("/home/bcorfman/dev/freytag-forge")
HERE = Path(__file__).resolve().parent
BASE = "bench/results/environment-narration/t9b-scope/probe2"


def _spec() -> str:
    return (
        "You are a RUNNER for one billed T9b second stage-P Jev classification probe in freytag-forge. "
        "Working directory: /home/bcorfman/dev/ringer-work/grounded-environment-narration-t9b-probe2. "
        "It sends 128 requests (64 frozen cases x 2 samples) through the project's local Worker /jev route. "
        "The preregistration is .plans/grounded-llm-environment-narration/t9b-probe2-prereg.md. HARD RULES: "
        "run COMMAND 1 EXACTLY ONCE in the FOREGROUND and never rerun it, even after an error or partial result. "
        "Do not edit any file. Do not print, echo, cat or log environment variables or the .env file "
        "or any credential. "
        "Do not git commit. A non-zero probe exit with partial rows is a valid outcome.\n\n"
        "COMMAND 1 (the billed run; run exactly once):\n"
        "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && "
        "(set -a; . ./.env; set +a; unset OPENAI_API_KEY RAILWAY_TOKEN RAILWAY_PROJECT_ID FREYTAG_TEST_CLOCK_TOKEN; "
        ".venv/bin/python scripts/ringer/environment_narration/under_question_probe.py --corpus v2 --run --confirm "
        "--max-calls 128 --max-usd 0.01 --out bench/results/environment-narration/t9b-scope/probe2/rows.json)\n\n"
        "COMMAND 2 (safe report render; may be rerun if needed):\n"
        "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && "
        ".venv/bin/python scripts/ringer/environment_narration/under_question_probe.py --corpus v2 --report "
        "--rows bench/results/environment-narration/t9b-scope/probe2/rows.json "
        "--out bench/results/environment-narration/t9b-scope/probe2/report.md\n\n"
        "Then print the report's probe gate section and say in one or two sentences what happened, including any "
        "stop reason. Do not interpret quality."
    )


def _check() -> str:
    return (
        "cd /home/bcorfman/dev/freytag-forge && set -o pipefail && "
        f"test -s {BASE}/rows.json && test -s {BASE}/report.md && "
        "(set -a; . ./.env; set +a; .venv/bin/python - <<'PY'\n"
        "import json\n"
        f"base={BASE!r}\n"
        "document=json.load(open(base+'/rows.json'))\n"
        "rows=document.get('rows')\n"
        "assert isinstance(rows,list) and (document.get('stop_reason') or "
        "len(rows)==128), 'missing stop reason or 128 rows'\n"
        "report=open(base+'/report.md').read()\n"
        "assert 'probe gate' in report.lower(), 'probe gate missing'\n"
        "text=open(base+'/rows.json').read()+report\n"
        "import os\n"
        "for name in (\n"
        "    'CLOUDFLARE_AI_TOKEN', 'CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_WORKER_TOKEN',\n"
        "    'OPENAI_API_KEY', 'RAILWAY_TOKEN', 'RAILWAY_PROJECT_ID', 'FREYTAG_TEST_CLOCK_TOKEN',\n"
        "):\n"
        "    value=os.environ.get(name,'').strip()\n"
        "    assert not value or value not in text, name+' leaked'\n"
        "print('integrity ok: %d rows, no credential in outputs' % len(rows))\n"
        "PY\n"
        ")\n"
    )


def _manifest() -> dict[str, Any]:
    return {
        "run_name": "grounded-environment-narration",
        "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9b-probe2",
        "max_parallel": 1,
        "worktrees": False,
        "repo": str(REPO),
        "tasks": [
            {
                "key": "billed-t9b-probe2",
                "task_type": "probe",
                "engine": "codex",
                "model": "gpt-5.6-luna",
                "engine_args": ["-c", "model_reasoning_effort=low"],
                "full_access": True,
                "max_attempts": 1,
                "timeout_s": 1800,
                "check_timeout_s": 300,
                "ownership": [BASE],
                "expect_files": [f"{REPO}/{BASE}/rows.json", f"{REPO}/{BASE}/report.md"],
                "spec": _spec(),
                "check": _check(),
                "verified": "probe rows and report rendered once under the approved ceiling",
            }
        ],
    }


def main(output_dir: Path | None = None) -> None:
    destination = HERE if output_dir is None else output_dir
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "run-t9b-probe2-live.json"
    target.write_text(json.dumps(_manifest(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
