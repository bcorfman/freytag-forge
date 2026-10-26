# ruff: noqa: E501
"""Generate the Ringer manifest that builds the sample-2 top-up harness (free; no billed call)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
ENV = "scripts/ringer/environment_narration"
OUT = Path(REPO) / ENV / "build-shadow2-topup.json"
PREREG = ".plans/grounded-llm-environment-narration/t8-shadow-sample2-topup-prereg.md"

COMMON = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "This work is FREE: no network, no model call, no billed run, never start a Worker, never read anything under bench/results/ (gitignored). Do not git commit. "
    f"Read {PREREG} first: it is the approved preregistration for a short top-up to the second shadow sample (route `observe_topup`, 9 commands). "
    "METHOD: write the failing tests first, confirm they fail, then implement. Sample 1 and sample 2 files, scripts and outputs must stay byte-identical except where this spec names an edit."
)

SPEC_A = (
    COMMON
    + " YOU MAY EDIT ONLY: scripts/ringer/transcript_1a/live_baseline.py; create scripts/ringer/environment_narration/shadow_sample2_topup.sh and tests/test_shadow_sample2_topup_harness.py. "
    "TASK 1 (route). In live_baseline.py add a route to `ROUTES` named `observe_topup`: exactly these 9 strings in this order: "
    "'inspect the drawer', 'pull out the drawer', 'feel under the drawer', 'feel under the drawer', 'go outside', 'inspect the truck', 'enter the truck', 'pick up my laptop', 'inspect the passenger seat'. "
    "Check how `--route observe` is special-cased anywhere in live_baseline.py (for example the `observe` route name tested for observation mode, shadow mode or the argparse choices) and make `observe_topup` behave exactly like `observe` in every such place (same observation mode, same shadow record, same summary fields); do not change what `observe` does. "
    "TASK 2 (script). Create shadow_sample2_topup.sh by copying scripts/ringer/environment_narration/shadow_sample2.sh and changing only: the header comment (point at the top-up preregistration), usage text `usage: shadow_sample2_topup.sh smoke|full`, stage limits (smoke: `--replicates 1 --max-calls 70`, MAX_USD=0.03; full: `--replicates 10 --max-calls 600`, MAX_USD=0.20), the output directory `bench/results/environment-narration/shadow-sample2-topup/$STAGE`, and the route argument `--route observe_topup`. Keep port 8793, the 'port already in use' exit 4, the local Worker cap, the credential unsets and every other line. Do not modify shadow_sample2.sh. Make the new file executable if shadow_sample2.sh is. "
    "TESTS (new file tests/test_shadow_sample2_topup_harness.py, model it on tests/test_shadow_sample2_harness.py): (a) ROUTES['observe_topup'] equals the 9 commands exactly and ROUTES['observe'] is unchanged (13 commands); (b) `bash -n` passes on the new script and its text contains `shadow-sample2-topup`, `observe_topup`, `70`, `600`, `0.03`, `0.20`, `8793`, and does not contain `shadow-sample2/` or `shadow-sample/`; (c) an unknown stage exits 2 with stdout empty and stderr exactly `usage: shadow_sample2_topup.sh smoke|full`; (d) a dry run (`--route observe_topup --shadow --replicates 1 --dry-run --out <tmp_path>`, as in test_observe_shadow_dry_run_records_planned_calls_without_real_calls) records route `observe_topup`, 9 turns, real_calls 0, calls_made > 0, and each turn row has the same keys it has on the `observe` route; (e) `shadow_report.py join` on synthetic rows shaped like a top-up (copy the row-building helpers from tests/test_shadow_report.py by importing or minimal local copies; 3 replicates of 9 turns with no scene change, two `feel under the drawer` observation turns each with empty relation lists and one `inspect the passenger seat` turn with an empty relation list per replicate, labels with `refind` and `invented_object` tags all false) prints `5 scene-transition turns drop the requirement: INCONCLUSIVE (n=0)` and the clause 7 and clause 8 lines with the right n and 'true=0' counts and does not raise. Do NOT edit shadow_report.py; if (e) shows the report fails on such rows, report the failure in your final message instead of fixing it. "
    "When done run the new test file, tests/test_shadow_sample2_harness.py and tests/test_environment_baseline.py (all must pass), then ruff check and ruff format on the files you touched, and report exact counts."
)
CHECK_A = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_sample2_topup_harness.py tests/test_shadow_sample2_harness.py tests/test_environment_baseline.py tests/test_shadow_report.py 2>&1 | tee /tmp/shadow2-topup-a.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/shadow2-topup-a.out && grep -Eq '[0-9]+ passed' /tmp/shadow2-topup-a.out && "
    f"test -f {ENV}/shadow_sample2_topup.sh && bash -n {ENV}/shadow_sample2_topup.sh && "
    f"git diff --quiet -- {ENV}/shadow_sample2.sh {ENV}/shadow_report.py && "
    f"! git status --porcelain | cut -c4- | grep -vE '^(scripts/ringer/transcript_1a/live_baseline.py|{ENV}/shadow_sample2_topup.sh|tests/test_shadow_sample2_topup_harness.py|{ENV}/[^ ]*shadow2[^ ]*|\\.plans/[^ ]*)$' | grep -q . && "
    f".venv/bin/python -m ruff check scripts/ringer/transcript_1a/live_baseline.py tests/test_shadow_sample2_topup_harness.py && .venv/bin/python -m ruff format --check scripts/ringer/transcript_1a/live_baseline.py tests/test_shadow_sample2_topup_harness.py"
)

SPEC_B = (
    COMMON
    + " YOU MAY EDIT ONLY: create scripts/ringer/environment_narration/make_shadow2_topup_run_manifests.py, run-shadow2-topup-smoke.json, run-shadow2-topup-full.json (same folder) and tests/test_shadow_sample2_topup_manifests.py. "
    "Another worker creates `shadow_sample2_topup.sh` (usage `shadow_sample2_topup.sh smoke|full`, output `bench/results/environment-narration/shadow-sample2-topup/<stage>`, route observe_topup, 9 turns per replicate); you only name it. "
    "Model the generator on make_shadow2_run_manifests.py in the same folder: read it and the existing run-shadow2-smoke.json / run-shadow2-full.json first. The new manifests are the sample-2 manifests with these changes only: task key `billed-shadow-sample2-topup-<stage>`; workdir `/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow2-topup-<stage>`; every script name `shadow_sample2.sh` becomes `shadow_sample2_topup.sh` and every output path `shadow-sample2/` becomes `shadow-sample2-topup/`; ownership and expect_files follow the new output path; the spec says the run is a top-up and is approved in `.plans/grounded-llm-environment-narration/t8-shadow-sample2-topup-prereg.md` (keep the sentence that the runner must not start unless the human's go for this stage was given in the task statement and the manifest is only launched by the orchestrator after the go) and states the stage numbers: smoke about 46 calls, cap 70 calls, ceiling $0.03; full about 460 calls, cap 600 calls, ceiling $0.20, expected about nine cents; it plays route `observe_topup` (9 commands). Keep every HARD RULE sentence of the sample-2 spec verbatim (run COMMAND 1 EXACTLY ONCE, NEVER run it a second time, Do not edit any file, no printing of environment variables or credentials, Do not git commit, the busy-port sentence, a non-zero exit with partial rows is valid). "
    "The check changes: spent_micro_usd ceiling 30000 for smoke and 200000 for full; expected replicates 1 for smoke and 10 for full; a complete run has 9 turns per replicate (not 13). Keep the credential-leak scan. Add to the check a content assertion for a completed run (stopped_reason is None): every replicate's last turn input is `inspect the passenger seat` and its 8th turn input is `pick up my laptop`. "
    "Do not rewrite the sample-2 manifests or generator; the new generator reads nothing from bench/results. "
    "TESTS (tests/test_shadow_sample2_topup_manifests.py, model on the manifest tests in tests/test_shadow_sample2_harness.py): both manifests exist and load; keys, workdirs, script names and output paths are the top-up ones and contain no `shadow-sample2/` and no `shadow_sample2.sh`; every hard-rule sentence is present; check text contains `summary['shadow']`, `spent_micro_usd`, the right ceiling, `== 9`, `pick up my laptop`; the generator is idempotent (running it leaves both files byte-identical); the sample-2 manifests are unchanged (compare to `git show HEAD:<path>` bytes). "
    "Run the new test file and tests/test_shadow_sample2_harness.py (all must pass), then ruff check and ruff format on the Python files you touched, and report exact counts."
)
CHECK_B = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_sample2_topup_manifests.py tests/test_shadow_sample2_harness.py 2>&1 | tee /tmp/shadow2-topup-b.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/shadow2-topup-b.out && grep -Eq '[0-9]+ passed' /tmp/shadow2-topup-b.out && "
    f"test -f {ENV}/run-shadow2-topup-smoke.json && test -f {ENV}/run-shadow2-topup-full.json && "
    f"git diff --quiet -- {ENV}/run-shadow2-smoke.json {ENV}/run-shadow2-full.json {ENV}/make_shadow2_run_manifests.py && "
    f"/home/bcorfman/dev/ringer/ringer.py lint {ENV}/run-shadow2-topup-smoke.json && /home/bcorfman/dev/ringer/ringer.py lint {ENV}/run-shadow2-topup-full.json && "
    f"! git status --porcelain | cut -c4- | grep -vE '^({ENV}/[^ ]*shadow2[^ ]*|{ENV}/shadow_sample2_topup.sh|scripts/ringer/transcript_1a/live_baseline.py|tests/test_shadow_sample2_topup_[a-z]*.py|\\.plans/[^ ]*)$' | grep -q . && "
    f".venv/bin/python -m ruff check {ENV}/make_shadow2_topup_run_manifests.py tests/test_shadow_sample2_topup_manifests.py && .venv/bin/python -m ruff format --check {ENV}/make_shadow2_topup_run_manifests.py tests/test_shadow_sample2_topup_manifests.py"
)


def _task(key: str, spec: str, check: str, owned: list[str], verified: str) -> dict:
    return {
        "key": key,
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 2400,
        "check_timeout_s": 900,
        "ownership": owned,
        "expect_files": [f"{REPO}/{owned[-1]}"],
        "spec": spec,
        "check": check,
        "verified": verified,
    }


manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow2-topup-build",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        _task(
            "shadow2-topup-route-and-script",
            SPEC_A,
            CHECK_A,
            [
                "scripts/ringer/transcript_1a/live_baseline.py",
                f"{ENV}/shadow_sample2_topup.sh",
                "tests/test_shadow_sample2_topup_harness.py",
            ],
            "route observe_topup (9 commands) and the topup script stages exist; the report handles a route with no scene change",
        ),
        _task(
            "shadow2-topup-run-manifests",
            SPEC_B,
            CHECK_B,
            [
                f"{ENV}/make_shadow2_topup_run_manifests.py",
                f"{ENV}/run-shadow2-topup-smoke.json",
                f"{ENV}/run-shadow2-topup-full.json",
                "tests/test_shadow_sample2_topup_manifests.py",
            ],
            "top-up smoke and full runner manifests with the approved caps and hard rules",
        ),
    ],
}
if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
