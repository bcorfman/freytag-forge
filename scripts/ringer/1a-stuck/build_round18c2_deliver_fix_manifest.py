# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18c-2: fixes to station 9 found in review. FREE: no model call, no network, no real gh or git push in tests.

One Codex task. Usage: build_round18c_deliver_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-deliver-fix"

OWNED = [
    "factory/stations/deliver.py",
    "tests/test_factory_deliver.py",
    "tests/shard_durations.json",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run a real `gh` or a real `ringer.py`, never `git push` to anything but a local temp bare repo. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/deliver.py` (station 9, read it fully first, and `tests/test_factory_deliver.py`) merges a factory-made fix ticket: it hashes the ticket tree's diff, commits and pushes a branch, opens a PR, waits for CI, merges with a merge commit, then waits for the staging deploy of the merged SHA. Between steps it may raise `LimitSleep` (CI pending, staging busy, deploy pending); the line then calls the handler AGAIN later with the same ticket, so every step must resume correctly from `<workspace>/<ticket>/delivery.json`. Review found two defects:

DEFECT 1, resume breaks. On every call the handler diffs the tree against `origin/main` and hashes it, then refuses an empty diff. After the PR is merged the change is in `origin/main`, so a resumed call (waiting for the deploy) sees an EMPTY diff and fails with "empty diff against origin/main" instead of finishing. The hash is also unstable: it changes after the commit (untracked-file diffs become tracked diffs) and when `main` moves. FIX: (a) when the record already has `merged_sha`, skip everything before the deploy wait (no tree diff, no hash, no protected-path check, no gates, no staged-run check) and go straight to the deploy wait and the final result; (b) make `diff_hash` a hash of CONTENT that is stable across commit, rebase and main advancing: take the changed paths as `git diff --name-only <merge-base>` plus untracked files, where `<merge-base>` is `git merge-base HEAD origin/main`, then hash the sorted list of (path, sha256 of that file's current working-tree bytes, or a marker for a deleted file). The protected-path and empty-diff checks use the same path list and run only before a PR exists.

DEFECT 2, rebase on a dirty tree. The rebase onto `origin/main` runs BEFORE the commit, and git refuses to rebase a tree with uncommitted changes, so it fails whenever `main` has moved. FIX: order the first-delivery steps as: create the branch, stage by explicit path, commit, THEN `git fetch origin main`, THEN rebase when behind (a conflict is a failure with the git output; abort the rebase with `git rebase --abort` first), THEN push.

TESTS to add or change in `tests/test_factory_deliver.py` (hermetic: stub `gh` runner, REAL local temp git repo plus a local bare repo as origin). Name them exactly: `test_resume_after_merge_waits_for_deploy_without_rediffing` (record has `merged_sha`, `origin/main` already contains the change so the diff is empty: the handler raises `LimitSleep("staging", ...)` while the deploy is pending and passes with the payload updates once the version matches, never failing on an empty diff and never calling `gh pr create` or merge); `test_behind_main_rebases_after_commit` (after the tree was created, another commit lands on origin main touching a different file: delivery rebases cleanly, the pushed branch contains both, PR created once); `test_rebase_conflict_fails_with_git_output` (conflicting main commit: failure, rebase aborted, tree left clean); `test_diff_hash_is_stable_across_commit_and_main_advance` (the hash computed before the commit equals the hash recomputed after the commit and after an unrelated main commit, so a resume after a CI sleep never reports `diff changed`); `test_changed_content_after_start_still_fails` (editing a file after the record was written does fail with `diff changed after delivery started`). Keep every existing test passing or update it only where the new behaviour requires, and keep the module story-agnostic. Each test file stays under 20 seconds. After the tests pass run `.venv/bin/python scripts/regen_shard_durations.py --missing-only`.

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit anything else. Write NOTES_18C2.txt (worktree root, never committed) listing every ambiguity and your choice."""

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
for name in test_resume_after_merge_waits_for_deploy_without_rediffing test_behind_main_rebases_after_commit test_rebase_conflict_fails_with_git_output test_diff_hash_is_stable_across_commit_and_main_advance test_changed_content_after_start_still_fails; do grep -q "def $name" tests/test_factory_deliver.py || { echo "missing test $name"; exit 1; }; done
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
git diff --cached > "$WORK/out/deliverfix.patch"
test -s "$WORK/out/deliverfix.patch"
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
        "run_name": "factory-deliver-fix",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "deliverfix",
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
    out = Path(__file__).with_name("round18c2-deliver-fix-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
