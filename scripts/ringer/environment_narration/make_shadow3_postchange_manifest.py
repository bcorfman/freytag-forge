# ruff: noqa: E501
"""Generate the Ringer manifest that builds the post-change shadow re-run harness (free; no billed call)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
ENV = "scripts/ringer/environment_narration"
OUT = Path(REPO) / ENV / "build-shadow3-postchange.json"
PREREG = ".plans/grounded-llm-environment-narration/t8-shadow-postchange-rerun-prereg.md"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "This work is FREE: no network, no model call, no billed run, never start a Worker, never read anything under bench/results/ (gitignored). Do not git commit. NEVER print or write any credential. "
    f"Read {PREREG} first: it is the approved preregistration for a re-run of the sample-2 top-up route (`observe_topup`, 9 commands, already in live_baseline.py) after the shadow verifier was fixed to judge the post-change world. "
    "The top-up files (shadow_sample2_topup.sh, run-shadow2-topup-*.json, make_shadow2_topup_*.py, tests/test_shadow_sample2_topup_*.py) and live_baseline.py must stay byte-identical. "
    "YOU MAY CREATE ONLY: scripts/ringer/environment_narration/shadow_sample3_postchange.sh, scripts/ringer/environment_narration/make_shadow3_postchange_run_manifests.py, scripts/ringer/environment_narration/run-shadow3-postchange-smoke.json, scripts/ringer/environment_narration/run-shadow3-postchange-full.json, tests/test_shadow_sample3_postchange_harness.py. "
    "METHOD: write the failing tests first, confirm they fail, then implement. "
    "TASK 1 (script). Copy scripts/ringer/environment_narration/shadow_sample2_topup.sh to shadow_sample3_postchange.sh and change only: the header comment (point at the re-run preregistration above), the usage text (`usage: shadow_sample3_postchange.sh smoke|full`), the output directory (`bench/results/environment-narration/shadow-sample3-postchange/$STAGE`) and the port (8794). Keep the stage limits (smoke: `--replicates 1 --max-calls 70`, MAX_USD=0.03; full: `--replicates 10 --max-calls 600`, MAX_USD=0.20), `--route observe_topup --shadow`, the busy-port refusal (exit 4) and everything else exactly as in the top-up script. "
    "TASK 2 (manifests). Write make_shadow3_postchange_run_manifests.py, modelled on make_shadow2_topup_run_manifests.py but deriving from the TOP-UP manifests run-shadow2-topup-{smoke,full}.json by string replacement (it must ASSERT every replacement matched, as the top-up generator does; a silent miss is a known past failure). Replace: `shadow-sample2-topup` -> `shadow-sample3-postchange`, `shadow_sample2_topup.sh` -> `shadow_sample3_postchange.sh`, the task key `billed-shadow-sample2-topup-{stage}` -> `billed-shadow-sample3-postchange-{stage}`, the workdir suffix `shadow2-topup-{stage}` -> `shadow3-postchange-{stage}`, and the approval sentence (the one beginning `This run is a top-up approved in the sample-2 preregistration`) with: `This run is a re-run of the top-up route under the corrected shadow order, approved in the preregistration "
    + PREREG
    + ", and the runner must not start unless the human's go for this stage was given in the task statement (the manifest is only launched by the orchestrator after the go). It uses about 50 calls, cap 70 calls, ceiling $0.03.` for smoke, and the same text with `about 495 calls, cap 600 calls, ceiling $0.20; expected about nine cents.` for full. Everything else (hard rules, check logic with 30000 / 200000 micro-USD ceilings, 9 turns per row, pick-up at turn 8, seat at turn 9, credential-leak scan) stays as in the top-up manifests with the paths replaced. Run the generator to write the two manifests. "
    "TESTS (new file tests/test_shadow_sample3_postchange_harness.py, model on tests/test_shadow_sample2_topup_manifests.py and the script checks in tests/test_shadow_sample2_topup_harness.py): (a) `bash -n` passes on the new script and its text has `shadow-sample3-postchange`, `observe_topup`, `70`, `600`, `0.03`, `0.20`, `8794` and not `shadow-sample2` or `8793`; (b) both manifests exist, carry only sample-3 paths (no `shadow-sample2`, no `shadow_sample2`, no `topup`), key, workdir, the exact numbers above in spec and check, the one-run hard rules, the `observe_topup` route and its 9 commands; (c) re-running the generator into the same files leaves them byte-identical; (d) the top-up manifests and script are unchanged versus `git show HEAD:<path>`. "
    "When done run the new test file, tests/test_shadow_sample2_topup_harness.py, tests/test_shadow_sample2_topup_manifests.py and tests/test_shadow_sample2_harness.py (all must pass), then ruff check and ruff format on the Python files you created, and report exact counts."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov "
    "tests/test_shadow_sample3_postchange_harness.py tests/test_shadow_sample2_topup_harness.py tests/test_shadow_sample2_topup_manifests.py tests/test_shadow_sample2_harness.py tests/test_shadow_report.py 2>&1 | tee /tmp/shadow3-build.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/shadow3-build.out && grep -Eq '[0-9]+ passed' /tmp/shadow3-build.out && "
    f"bash -n {ENV}/shadow_sample3_postchange.sh && test -f {ENV}/run-shadow3-postchange-smoke.json && test -f {ENV}/run-shadow3-postchange-full.json && "
    f"git diff --quiet -- {ENV}/shadow_sample2_topup.sh {ENV}/run-shadow2-topup-smoke.json {ENV}/run-shadow2-topup-full.json scripts/ringer/transcript_1a/live_baseline.py && "
    f"test -z \"$(git status --porcelain | cut -c4- | grep -vE '^({ENV}/(shadow_sample3_postchange.sh|make_shadow3_postchange[a-z_]*.py|run-shadow3-postchange-(smoke|full).json|build-shadow3-postchange.json)|tests/test_shadow_sample3_postchange_harness.py|\\.plans/.*)$')\" && "
    f".venv/bin/python -m ruff check {ENV}/make_shadow3_postchange_run_manifests.py tests/test_shadow_sample3_postchange_harness.py && "
    f".venv/bin/python -m ruff format --check {ENV}/make_shadow3_postchange_run_manifests.py tests/test_shadow_sample3_postchange_harness.py"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow3-postchange-build",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "shadow3-postchange-harness",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 900,
            "ownership": [
                f"{ENV}/shadow_sample3_postchange.sh",
                f"{ENV}/make_shadow3_postchange_run_manifests.py",
                f"{ENV}/run-shadow3-postchange-smoke.json",
                f"{ENV}/run-shadow3-postchange-full.json",
                "tests/test_shadow_sample3_postchange_harness.py",
            ],
            "expect_files": [
                f"{REPO}/{ENV}/shadow_sample3_postchange.sh",
                f"{REPO}/{ENV}/run-shadow3-postchange-smoke.json",
                f"{REPO}/{ENV}/run-shadow3-postchange-full.json",
                f"{REPO}/tests/test_shadow_sample3_postchange_harness.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the post-change re-run harness exists, carries only its own paths and numbers, and leaves the top-up untouched",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
