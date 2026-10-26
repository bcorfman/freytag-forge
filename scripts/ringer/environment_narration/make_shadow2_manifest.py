# ruff: noqa: E501
"""Generate the Ringer manifest that builds the second shadow-sample harness (report clauses, script, runner manifests)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-shadow2-harness.json"
PREREG = ".plans/grounded-llm-environment-narration/t8-shadow-sample2-prereg.md"
ENV = "scripts/ringer/environment_narration"

COMMON = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "NEVER make a billed or network call, never start the local Worker, never run a live route (a `--dry-run` of live_baseline.py is allowed and free). Do not git commit. NEVER print or write any credential, never read .env. NO regular expressions in new code. "
    "Tests must be hermetic: use only synthetic rows built in the test, NEVER read anything under bench/results/ (it is gitignored and absent on CI). "
    "METHOD: write the new tests FIRST, run them to see them fail for the right reason, then implement. "
    f"READ FIRST: {PREREG} (the approved preregistration; the section 'Gate' and 'Defect tags' define what you build), and the existing {ENV}/shadow_report.py with tests/test_shadow_report.py. "
    "AT THE END run ruff check and ruff format over every file you added or changed and report exact test counts."
)

SPEC_REPORT = (
    COMMON
    + f" TASK 1 of 2: extend the blind-label report with the second sample's new clauses. YOU MAY EDIT ONLY: {ENV}/shadow_report.py and tests/test_shadow_report.py. "
    "DESIGN. `shadow_report.py join rows.json labels.json` already prints the sample-1 gate (clauses 1 to 4 and 2b) and returns a report. Keep every existing output line and behavior byte-identical for rows and labels that do not use the new features (existing tests must pass unchanged). Add: "
    "(a) Labels template and labels: each observation turn's label object may carry two optional booleans `refind` and `invented_object` (the `labels-template` output includes both keys as null for every turn; a join with them null or absent must NOT report them missing and must not change the old gate output). "
    "(b) A new gate section printed after the existing clauses, with these exact clause names: "
    "'5 scene-transition turns drop the requirement': a scene-transition turn is any turn in the rows whose scene changed during the turn (look at the real row shape: rows hold `scene`, `before`, `after`, `places_before`, `places_after`, `observation_shadow`; in the saved sample-1 rows a turn's `scene` field and the neighbouring turns show the scene id; the harness writes the scene id AFTER the turn in `scene`, so compare it with the previous turn's `scene` in the same replicate; for the first turn of a replicate there is no transition). NOTE: a transition turn that dropped its requirement makes no verifier request, so its `observation_relations` is None and it is NOT an observation turn; scan ALL turns (`_turns`), not `_observation_turns`. Pass when every such turn has an `observation_shadow` dict with key `requirement_dropped` equal to 'scene_or_area_changed' and `requests` equal to 0, or has `observation_shadow` None because the turn made no narrator call; FAIL naming the turn ids otherwise; INCONCLUSIVE when there are zero transition turns. "
    "'6 held-item mention relations': print, for relations whose `holder` is not null/empty, a small table of verdict counts by hand label (reported only, never a pass/fail by itself; those relations already count in clauses 1, 2 and 2b). "
    "'7 re-find of the held card': among observation turns whose command is `feel under the drawer` (casefold compare of the command text, the route command, ignoring a trailing period) AND whose label `refind` is true or false (not null), count refind true. PASS when n >= 15 and refind true <= 1; FAIL when n >= 15 and true > 1; INCONCLUSIVE when n < 15. Print n and the count. "
    "'8 invented object on the empty seat': among observation turns whose command is `inspect the passenger seat` (same normalised compare) AND whose label `invented_object` is true or false, where the seat was empty: empty means the narration's `places_before` shows the laptop held by the protagonist rather than on the seat (look at the real `places_before` shape in the test helper of tests/test_shadow_report.py and in the real rows; `places_before` maps entity id to its parent id (for example the laptop to the protagonist when it is held), so implement the emptiness test generically as: no value in `places_before` equals the id in `observation_request.focus` (an empty seat turn in the saved rows has `observation_relations` == [] and shadow outcome 'no_relations'); if you cannot decide it from the row fields, fall back to treating a turn as empty when its `observation_relations` is an empty list and say so in a comment). PASS when n >= 6 and true <= 1; FAIL when n >= 6 and true > 1; INCONCLUSIVE when n < 6. "
    "(c) The overall result line must say verifier gate (clauses 1 to 6) and product-defect gate (clauses 7 and 8) SEPARATELY, matching the preregistration: a failure of 7 or 8 never flips the verifier gate, and an INCONCLUSIVE clause is shown as such. Commands and focus names are compared as data from the rows; the report code must contain no story-specific vocabulary other than the two route command strings as constants named clearly at the top of the module (`REFIND_COMMAND`, `SEAT_COMMAND`). "
    "TESTS (synthetic rows only; extend tests/test_shadow_report.py): transition turn passes with requirement_dropped and requests 0; fails when a transition turn asked the verifier; zero transitions is inconclusive; clause 7 and 8 pass, fail and inconclusive at the thresholds (1 allowed, 2 fails; n at the minimum); null tags are not 'missing'; the template includes the new keys; old output is unchanged for rows without the new keys (reuse the existing tests' expectations). Also run tests/test_shadow_report.py and tests/test_observation_shadow.py."
)

SPEC_SCRIPT = (
    COMMON
    + f" TASK 2 of 2: sample-2 runner script and runner manifests. YOU MAY EDIT ONLY: the NEW files {ENV}/shadow_sample2.sh, {ENV}/make_shadow2_run_manifests.py, {ENV}/run-shadow2-smoke.json, {ENV}/run-shadow2-full.json and tests/test_shadow_sample2_harness.py. Never edit {ENV}/shadow_sample.sh or the sample-1 run manifests (sample 1's artifacts must stay untouched). "
    f"READ ALSO: {ENV}/shadow_sample.sh, {ENV}/run-shadow-smoke.json and {ENV}/run-shadow-full.json (the sample-1 versions), scripts/ringer/transcript_1a/live_baseline.py (flags `--route observe --shadow --replicates --turns --max-calls --confirm --out --dry-run`). "
    "BUILD. (1) shadow_sample2.sh: a copy of shadow_sample.sh with these differences only: stages `smoke` = `--replicates 1 --max-calls 100` (the FULL 13-turn route, no `--turns`), MAX_USD=0.05; `full` = `--replicates 10 --max-calls 900`, MAX_USD=0.30; output directory `bench/results/environment-narration/shadow-sample2/$STAGE`; PORT 8793 (so it cannot collide with sample 1's); the header comment points at the sample-2 preregistration. An unknown stage exits 2 with a usage message before doing anything else (before sourcing .env, before any port check). (2) make_shadow2_run_manifests.py: a generator that reads the two sample-1 run manifests and writes run-shadow2-smoke.json and run-shadow2-full.json, changing: keys (billed-shadow-sample2-smoke / -full), workdir names (grounded-environment-narration-shadow2-smoke / -full), every path and description from shadow-sample to shadow-sample2, the command to `bash scripts/ringer/environment_narration/shadow_sample2.sh <stage>`, the call and dollar numbers in the spec text (smoke: about 67 calls, cap 100 calls, ceiling $0.05; full: about 670 calls, cap 900 calls, ceiling $0.30, expected about thirteen cents), the approval reference to the sample-2 preregistration, and the check: it must (i) assert the rows file and summary exist, `summary['shadow']` is True and spent <= the ceiling in micro-USD (50000 smoke, 300000 full), AND (ii) assert a stop reason or the row count: either `summary['stopped_reason']` is not null, or the number of replicates equals 1 (smoke) / 10 (full) and every replicate has 13 turns, AND (iii) keep the sample-1 credential-leak scan. Keep every HARD RULE sentence of the sample-1 spec (run COMMAND 1 exactly once, never rerun, no edits, no env printing, no commit, port refusal exit 4 explained, a non-zero exit with partial rows is valid) and the sentence that the human must approve is replaced by: approved in the sample-2 preregistration, and the runner must not start unless the human's go for this stage was given in the task statement (the manifest is only launched by the orchestrator after the go). Run the generator to produce the two JSON files and commit nothing. "
    "TESTS in tests/test_shadow_sample2_harness.py (hermetic, no network, no bench/results reads): `bash -n` passes on shadow_sample2.sh; an unknown stage exits 2 with usage and starts nothing (run the script with a bogus stage in a subprocess with an empty environment; it must exit before anything else); the script text contains `shadow-sample2`, the caps (100/900) and the dollar ceilings (0.05/0.30) and does NOT contain the sample-1 output path `shadow-sample/` or the port 8792; both run manifests load as JSON, name only the sample-2 paths, contain the one-run hard-rule sentences, and their checks mention the row count assertion and the ceiling; the generator is idempotent (running it again yields byte-identical files); `live_baseline.py --route observe --shadow --replicates 1 --dry-run` exits 0 and its output mentions the planned call count (run it in a subprocess with CLOUDFLARE_WORKER_URL unset; if the dry run needs the environment, set only a fake URL; it must make no network call). Then run `bash -n` and lint the two manifests with `cd /home/bcorfman/dev/ringer && ./ringer.py lint <path>`."
)

CHECK_REPORT = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_report.py tests/test_observation_shadow.py 2>&1 | tee /tmp/shadow2-report.out | tail -8 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/shadow2-report.out && grep -Eq '[0-9]+ passed' /tmp/shadow2-report.out && "
    f"grep -q 'REFIND_COMMAND' {ENV}/shadow_report.py && grep -q 'SEAT_COMMAND' {ENV}/shadow_report.py && "
    f"! git status --porcelain | cut -c4- | grep -vE '^({ENV}/shadow_report.py|tests/test_shadow_report.py|{ENV}/[^ ]*shadow2[^ ]*|{ENV}/(shadow_sample2.sh|run-shadow2-[a-z]+.json)|tests/test_shadow_sample2_harness.py)$' | grep -q . && "
    f".venv/bin/python -m ruff check {ENV}/shadow_report.py tests/test_shadow_report.py && .venv/bin/python -m ruff format --check {ENV}/shadow_report.py tests/test_shadow_report.py"
)

CHECK_SCRIPT = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    f"bash -n {ENV}/shadow_sample2.sh && test -s {ENV}/run-shadow2-smoke.json && test -s {ENV}/run-shadow2-full.json && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_sample2_harness.py 2>&1 | tee /tmp/shadow2-script.out | tail -8 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/shadow2-script.out && grep -Eq '[0-9]+ passed' /tmp/shadow2-script.out && "
    f"! grep -q 'shadow-sample/' {ENV}/shadow_sample2.sh && grep -q 'shadow-sample2' {ENV}/shadow_sample2.sh && "
    f"git diff --quiet -- {ENV}/shadow_sample.sh {ENV}/run-shadow-full.json {ENV}/run-shadow-smoke.json && "
    f"(cd /home/bcorfman/dev/ringer && ./ringer.py lint /home/bcorfman/dev/freytag-forge/{ENV}/run-shadow2-smoke.json && ./ringer.py lint /home/bcorfman/dev/freytag-forge/{ENV}/run-shadow2-full.json) && "
    f".venv/bin/python -m ruff check {ENV}/make_shadow2_run_manifests.py tests/test_shadow_sample2_harness.py && .venv/bin/python -m ruff format --check {ENV}/make_shadow2_run_manifests.py tests/test_shadow_sample2_harness.py"
)

TASK = {
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=high"],
    "full_access": True,
    "max_attempts": 2,
    "timeout_s": 3600,
    "check_timeout_s": 900,
}

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow2-harness",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            **TASK,
            "key": "shadow2-report-clauses",
            "ownership": [f"{ENV}/shadow_report.py", "tests/test_shadow_report.py"],
            "expect_files": [f"{REPO}/tests/test_shadow_report.py"],
            "spec": SPEC_REPORT,
            "check": CHECK_REPORT,
            "verified": "join prints clauses 5 to 8 with pass, fail and inconclusive; old output unchanged; verifier and defect gates are reported separately",
        },
        {
            **TASK,
            "key": "shadow2-script-and-manifests",
            "ownership": [
                f"{ENV}/shadow_sample2.sh",
                f"{ENV}/make_shadow2_run_manifests.py",
                f"{ENV}/run-shadow2-smoke.json",
                f"{ENV}/run-shadow2-full.json",
                "tests/test_shadow_sample2_harness.py",
            ],
            "expect_files": [f"{REPO}/{ENV}/shadow_sample2.sh", f"{REPO}/{ENV}/run-shadow2-full.json"],
            "spec": SPEC_SCRIPT,
            "check": CHECK_SCRIPT,
            "verified": "the sample-2 script and runner manifests exist, are sample-2-only, carry the one-run hard rules and a row-count assertion, and leave sample 1 untouched",
        },
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
