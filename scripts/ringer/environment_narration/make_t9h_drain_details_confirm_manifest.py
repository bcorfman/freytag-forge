# ruff: noqa: E501
"""Write the Ringer manifest that fixes the drain-details probe label freeze and adds the confirmation stage."""

import json
from pathlib import Path

ROOT = "/home/bcorfman/dev/freytag-forge"
PY = f"{ROOT}/.venv/bin/python"
CHECK = f"{ROOT}/scripts/ringer/environment_narration/check_t9h_drain_details_confirm.sh"
OWNED = [
    f"{ROOT}/scripts/ringer/environment_narration/drain_details_prose_probe.py",
    f"{ROOT}/scripts/ringer/environment_narration/enforce_t9h_drain_details.sh",
    f"{ROOT}/tests/test_drain_details_prose_probe.py",
    f"{ROOT}/.plans/grounded-llm-environment-narration/t9h-drain-details-prereg.md",
]
SPEC = (
    f"Working directory: {ROOT} (Python 3.12). Run Python as `{PY}` only (never uv). Run tests with: `export "
    f"PYTHONPATH={ROOT} TMPDIR=/tmp; env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN {PY} -m pytest -q "
    "-p no:cacheprovider --no-cov <files>`. No network, no model call, no billed call, no Worker, no credentials, never "
    "read or print .env. Do not git commit. NO regular expressions in new code. Match the surrounding code's style. The "
    "working tree holds unrelated uncommitted edits: touch ONLY the files you own, never run git checkout, stash, reset "
    "or clean, and do not touch anything under bench/results/. At the end run ruff check --fix and ruff format on the .py "
    f"files you own. FILES YOU OWN: {', '.join(OWNED)}.\n\n"
    "BACKGROUND. scripts/ringer/environment_narration/drain_details_prose_probe.py (read it, its tests and wrapper "
    "enforce_t9h_drain_details.sh, and the prereg) ran once as a 20-call screen. Two things must change.\n"
    "1. FREEZE BUG. `sheets()` currently ends with `write_label_freeze(labels_path)` on the EMPTY labels_template.json, "
    "so `report()` can never match a filled label file against `labels.freeze.json`. Fix it: `sheets()` must no longer "
    "write the freeze. Add a CLI mode `--freeze-labels` (needs `--labels`) that writes `labels.freeze.json` beside the "
    "labels file holding the SHA-256 of that labels file, refusing if the file has any null label or a freeze already "
    "exists with a different hash (never silently overwrite a freeze). `report()` keeps requiring a matching freeze and "
    "must give the clear error 'run --freeze-labels first' when none exists. Update tests accordingly (a filled labels "
    "file, frozen, then reported; no freeze -> clear error; edited labels after the freeze -> hash mismatch error).\n"
    "2. CONFIRMATION STAGE. The wrapper gets a second stage: `enforce_t9h_drain_details.sh confirm` runs the SAME probe "
    "with `--samples 15 --max-calls 30 --max-usd 0.06`, a local Worker on port 8805 with `--max-usd 0.06`, output "
    "directory bench/results/environment-narration/t9h-drain-details/confirm, and the same refuse-if-rows-exist and "
    "port-in-use guards. The existing `screen` stage is unchanged. The probe's partial-run rule stays: fewer rows than "
    "planned is INCONCLUSIVE. Add a dated addendum (2026-10-30) to the prereg: the screen stopped at 19 of 20 rows "
    "because the local Worker's own budget guard returned 429 at $0.0223 spent of a $0.03 cap (it reserves headroom per "
    "call); the user raised the cap for the separate 15-per-arm confirmation to $0.06 with a 30-call limit; the gate is "
    "unchanged (control reproduces the defect with at least 1 forbidden row, candidate has zero forbidden rows, "
    "complete run); the confirmation is a new run in a new directory, the screen rows are never rerun or edited; the "
    "plot.md edit stays conditional on the confirmation passing. The addendum must contain the words 'confirmation' and "
    "'0.06'. Do not change the frozen case text or the single edit.\n\n"
    f"HOW TO VERIFY BEFORE YOU FINISH: run `bash {CHECK}`. Do not edit the check. Finish with a short summary."
)
manifest = {
    "run_name": "t9h-drain-rejection-p1-p3",
    "workdir": "/home/bcorfman/dev/ringer-work/t9h-drain-rejection-p1-p3",
    "max_parallel": 1,
    "worktrees": False,
    "repo": ROOT,
    "tasks": [
        {
            "key": "fix-freeze-add-confirm",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 900,
            "ownership": OWNED,
            "expect_files": OWNED,
            "verified": "tests green, ruff clean, freeze flow fixed, confirm stage dry-runs 30 calls under the 0.06 cap",
            "spec": SPEC,
            "check": f"bash {CHECK}",
        }
    ],
}
out = Path(__file__).with_name("run-t9h-drain-details-confirm-build.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
