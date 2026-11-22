# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18c-4: station 9 fixes found in the second real run. FREE: no model call, no network, no real gh or git push in tests.

One Codex task. Usage: build_round18c_deliver_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-deliver-fix4"

OWNED = [
    "factory/stations/deliver.py",
    "tests/test_factory_deliver.py",
    "tests/shard_durations.json",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run a real `gh` or `ringer.py`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/deliver.py` (station 9; read it and `tests/test_factory_deliver.py` first) runs `gh` and `git` through `_default_runner`, which returns stdout and stderr joined together. The second real run failed on that: real `gh pr view <n> --json statusCheckRollup,state` prints its JSON on stdout and a multi-line `hint:` notice on stderr, so joined output is not valid JSON and the station stopped with `could not inspect pull request checks`. The same joined output also hid the PR number in `gh pr create` earlier (URL on stdout, notices on stderr).

FIX 1. `_default_runner` returns STDOUT ONLY when the exit code is 0, and stdout followed by stderr when it is not (so failures still show their reason). Every JSON parse and URL parse then sees only what the command printed on stdout. Keep `_one_line` redaction on anything put in a result message.

FIX 2. `gh pr merge --delete-branch` can exit non-zero AFTER the merge succeeded (it also tries to delete the local branch, which is checked out in the ticket's worktree). So after a failed merge call, always read `gh pr view <n> --json mergeCommit,state`; when `state` is `MERGED` carry on exactly as after a successful merge (record `merged_sha` and `merged_at`); only when it is not merged fail with `could not merge pull request`. Also, on every call that has a `pr_number` but no `merged_sha`, read the PR state FIRST: a `MERGED` PR skips the CI and merge steps and records the merge commit; a `CLOSED` PR (not merged) fails with `pull request closed without merging`.

TESTS in `tests/test_factory_deliver.py` (hermetic; no real gh). Name them exactly: `test_default_runner_returns_stdout_only_on_success` (a fake executable script in a temp dir, called through `_default_runner`, prints JSON on stdout and a hint block on stderr and exits 0: the result is the JSON alone and parses), `test_default_runner_includes_stderr_on_failure` (the same script exiting 1 returns stdout plus stderr), `test_merge_command_failing_after_the_merge_still_succeeds` (stub `gh pr merge` exits 1 but `gh pr view` then says MERGED with a merge commit: the station records `merged_sha` and carries on to the deploy wait), `test_merge_command_failing_and_not_merged_fails` (view says OPEN: failure `could not merge pull request`), `test_resume_with_already_merged_pr_skips_ci_and_merge` (record has `pr_number` but no `merged_sha`; view says MERGED: no merge call, no CI wait, record updated), `test_closed_pr_fails`. Existing tests keep passing. Test file stays under 25 seconds. Then run `.venv/bin/python scripts/regen_shard_durations.py --missing-only`.

HARD LIMITS. Edit only the owned files: @OWNED@. Write NOTES_18C4.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out" "$WORK/fakebin"
printf '#!/bin/sh\\necho "real gh was called: $*" >> %s/gh-called.txt\\nexit 99\\n' "$WORK/out" > "$WORK/fakebin/gh"
chmod +x "$WORK/fakebin/gh"
rm -f "$WORK/out/gh-called.txt"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF @ALLOW_ARGS@ || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity|reyes|1A" factory/stations/deliver.py; then echo "story-specific word in deliver.py"; exit 1; fi
grep -q -- "--merge" factory/stations/deliver.py || { echo "merge commit flag missing"; exit 1; }
if grep -n -E -- "--squash|--rebase|--admin|--auto" factory/stations/deliver.py; then echo "forbidden merge flag"; exit 1; fi
grep -q "staged_run.lock" factory/stations/deliver.py || { echo "staged lock check missing"; exit 1; }
grep -q "merge_to_main" factory/line.py || { echo "merge_to_main routing missing in line.py"; exit 1; }
for name in test_default_runner_returns_stdout_only_on_success test_default_runner_includes_stderr_on_failure test_merge_command_failing_after_the_merge_still_succeeds test_merge_command_failing_and_not_merged_fails test_resume_with_already_merged_pr_skips_ci_and_merge test_closed_pr_fails; do grep -q "def $name" tests/test_factory_deliver.py || { echo "missing test $name"; exit 1; }; done
grep -q "test_factory_deliver.py" tests/shard_durations.json || { echo "shard_durations.json lacks the new test file"; exit 1; }
start=$(date +%s)
PATH="$WORK/fakebin:$PATH" .venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_deliver.py tests/test_factory_line.py tests/test_factory_followups.py tests/test_factory_stations.py tests/test_factory_live_playtest.py tests/test_factory_wiring.py tests/test_factory_triage.py tests/test_factory_tickets.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
[ ! -e "$WORK/out/gh-called.txt" ] || { cat "$WORK/out/gh-called.txt"; echo "a test called the real gh"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_deliver.py tests/test_factory_line.py tests/test_factory_followups.py tests/test_factory_stations.py tests/test_factory_live_playtest.py
.venv/bin/python -m ruff format --check factory tests/test_factory_deliver.py tests/test_factory_line.py tests/test_factory_followups.py tests/test_factory_stations.py tests/test_factory_live_playtest.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
[ ! -e factory/state/staged_run.lock ] || { echo "a test left factory/state/staged_run.lock"; exit 1; }
git diff --cached > "$WORK/out/deliverfix4.patch"
test -s "$WORK/out/deliverfix4.patch"
"""


def build() -> dict:
    allow_args = " ".join(f"-e {path}" for path in OWNED)

    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_ARGS@", allow_args)
        )

    return {
        "run_name": "factory-deliver-fix4",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "deliverfix4",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "Station 9 merges a factory-made fix PR only after free gates and green CI, never during a staged run, with a merge commit and an idempotency record, then waits for the SHA-bound staging deploy and hands the ticket to station 7; tests use stubs and local temp git repos only.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18c4-deliver-fix-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
