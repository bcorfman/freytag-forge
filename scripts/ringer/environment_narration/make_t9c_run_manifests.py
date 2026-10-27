"""Generate the Ringer manifests for the T9c enforced runs."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
ENVIRONMENT_NARRATION = Path(REPO) / "scripts/ringer/environment_narration"


def _check(stage: str, replicates: tuple[int, int, int], micro_usd: int) -> str:
    base = f"bench/results/environment-narration/t9c-open/{stage}"
    return (
        "cd "
        + REPO
        + " && set -o pipefail && .venv/bin/python - <<'PY'\n"
        + "import json\n"
        + "import os\n"
        + "from pathlib import Path\n\n"
        + f'base = Path("{base}")\n'
        + f'assert json.loads((base / "spent.json").read_text())["spent_micro_usd"] <= {micro_usd}\n\n'
        + "def route_rows(name, expected_replicates, expected_turns, last_input):\n"
        + '    route_base = base / name / "rows"\n'
        + '    assert (route_base / "rows.json").is_file()\n'
        + '    assert (route_base / "summary.json").is_file()\n'
        + '    rows = json.loads((route_base / "rows.json").read_text())\n'
        + '    summary = json.loads((route_base / "summary.json").read_text())\n'
        + '    assert summary["enforce"] is True\n'
        + '    assert summary.get("shadow", False) is False\n'
        + "    for row in rows:\n"
        + '        for turn in row.get("turns", []):\n'
        + '            for field in ("turn_elapsed_s", "enforce_attempts", "narration_attempts", '
        + '"observation_request", "engine_opened", "focus_open_state_after", '
        + '"focus_open_state_committed", "handoff_id", "delivered_text"):\n'
        + "                assert field in turn\n"
        + '    if summary.get("stopped_reason") is None:\n'
        + "        assert len(rows) == expected_replicates\n"
        + '        assert all(len(row.get("turns", [])) == expected_turns for row in rows)\n'
        + '        assert all(row["turns"][-1]["input"] == last_input for row in rows)\n\n'
        + f'route_rows("a", {replicates[0]}, 9, "inspect the passenger seat")\n'
        + 'a_summary = json.loads((base / "a" / "rows" / "summary.json").read_text())\n'
        + 'if a_summary.get("stopped_reason") is None:\n'
        + f'    route_rows("b", {replicates[1]}, 4, "pull out the drawer")\n'
        + '    b_summary = json.loads((base / "b" / "rows" / "summary.json").read_text())\n'
        + '    if b_summary.get("stopped_reason") is None:\n'
        + f'        route_rows("c", {replicates[2]}, 6, "look under the drawer")\n'
        + 'print("checked t9c routes and spent cap")\n'
        + "PY\n"
        + "(set -a; . ./.env; set +a; .venv/bin/python - <<'PY'\n"
        + "import os\n"
        + "from pathlib import Path\n\n"
        + f'base = Path("{base}")\n'
        + 'text = "".join(path.read_text(errors="replace") for path in base.rglob("*") if path.is_file())\n'
        + 'for name in ("CLOUDFLARE_AI_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_WORKER_TOKEN"):\n'
        + '    value = os.environ.get(name, "").strip()\n'
        + '    assert not value or value not in text, name + " value leaked into outputs"\n'
        + 'print("no credential value in outputs")\n'
        + "PY\n)"
    )


def _manifest(stage: str, args: tuple[str, str, str], usd: str, micro_usd: int) -> dict:
    args_a, args_b, args_c = args
    base = f"bench/results/environment-narration/t9c-open/{stage}"
    replicates = (1, 1, 2) if stage == "smoke" else (10, 5, 15)
    spec = (
        f"You are a RUNNER for one billed T9c open-container and repeatable-handoff enforced sample ({stage} stage) "
        f"in freytag-forge. Working directory: {REPO}. The approved preregistration is "
        ".plans/grounded-llm-environment-narration/t9c-engine-open-prereg.md. Run COMMAND 1 exactly once in the "
        "foreground; never rerun it, edit any file, commit, print no credential, or finish while it is running. "
        "The script uses one local Worker on port 8797, runs route A observe_topup, then route B observe_under_first, "
        "then route C observe_look_inside_under only when the prior summary has no stop reason. It has enforcement on, "
        "shadow off, 70B JSON off, a 20 second timeout, and no retry on timeout.\n\n"
        f"COMMAND 1: cd {REPO} && bash scripts/ringer/environment_narration/enforce_stage3.sh {stage}\n\n"
        f"The stage caps are route A {args_a}, route B {args_b}, route C {args_c}, and the one Worker cap is "
        f"--max-usd {usd}. A quota code, HTTP 429, HTTP 5xx, or call cap stops the stage and preserves partial rows. "
        f"Expected complete row counts are A {replicates[0]} x 9 turns, B {replicates[1]} x 4 turns, and "
        f"C {replicates[2]} x 6 turns. Do not interpret the results beyond reporting the script's non-secret output "
        "and spent.json."
    )
    return {
        "run_name": "grounded-environment-narration",
        "workdir": f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9c-{stage}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": REPO,
        "tasks": [
            {
                "key": f"billed-t9c-{stage}",
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
                    f"{REPO}/{base}/c/rows/rows.json",
                    f"{REPO}/{base}/c/rows/summary.json",
                    f"{REPO}/{base}/spent.json",
                ],
                "spec": spec,
                "check": _check(stage, replicates, micro_usd),
                "verified": "the T9c three-route enforcing-verifier sample ran once under the approved cap",
            }
        ],
    }


def main() -> None:
    manifests = {
        "smoke": (
            ("--replicates 1 --max-calls 90", "--replicates 1 --max-calls 40", "--replicates 2 --max-calls 90"),
            "0.07",
            70000,
        ),
        "full": (
            ("--replicates 10 --max-calls 800", "--replicates 5 --max-calls 250", "--replicates 15 --max-calls 700"),
            "0.45",
            450000,
        ),
    }
    for stage, (args, usd, micro_usd) in manifests.items():
        output = ENVIRONMENT_NARRATION / f"run-t9c-{stage}.json"
        output.write_text(json.dumps(_manifest(stage, args, usd, micro_usd), indent=1) + "\n")


if __name__ == "__main__":
    main()
