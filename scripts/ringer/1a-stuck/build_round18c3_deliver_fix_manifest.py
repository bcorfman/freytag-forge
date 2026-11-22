# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18c-3: station 9 fix found in the first real run. FREE: no model call, no network, no real gh or git push in tests.

One Codex task. Usage: build_round18c_deliver_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-deliver-fix3"

OWNED = [
    "factory/stations/deliver.py",
    "tests/test_factory_deliver.py",
    "tests/shard_durations.json",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run a real `gh` or `ringer.py`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/deliver.py` (station 9; read it and `tests/test_factory_deliver.py` first) opens a PR with `gh pr create` and reads the PR number from the command's output with `_pr_number`, whose regex only accepts a number at the very END of the output. The first real run failed: real `gh pr create` printed the PR URL (`https://github.com/<owner>/<repo>/pull/810`) followed by extra notice lines, so the number was not found and the station stopped with `could not read pull request number`, after the PR already existed.

FIX. (1) `_pr_number` takes the number from the first `/pull/<digits>` occurrence anywhere in the output (the URL form gh prints), and also accepts output that is only digits. Rename the misleading `_SHA_RE` to a name that says what it is. (2) When `gh pr create` succeeded but the number cannot be read from its output, fall back to `_find_pr` (same helper, lookup by branch with `gh pr list --head <branch> --state all --json number,state`) before giving up; only when both fail return `could not read pull request number`. (3) The PR number is written to `delivery.json` as soon as it is known, as today.

TESTS in `tests/test_factory_deliver.py` (hermetic, stub `gh`, REAL local temp git repos as in the existing tests). Name them exactly: `test_pr_number_read_from_url_followed_by_notice_lines` (create output is the URL, a blank line and two notice lines; delivery proceeds and the record holds the number), `test_pr_number_falls_back_to_branch_lookup` (create output has no number; the branch lookup returns it; delivery proceeds), `test_pr_number_unreadable_everywhere_fails` (both fail: the failure message above, no merge call). Existing tests keep passing. Test file stays under 20 seconds. Then run `.venv/bin/python scripts/regen_shard_durations.py --missing-only`.

HARD LIMITS. Edit only the owned files: @OWNED@. Write NOTES_18C3.txt (worktree root, never committed) listing every ambiguity and your choice."""

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
for name in test_pr_number_read_from_url_followed_by_notice_lines test_pr_number_falls_back_to_branch_lookup test_pr_number_unreadable_everywhere_fails; do grep -q "def $name" tests/test_factory_deliver.py || { echo "missing test $name"; exit 1; }; done
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
git diff --cached > "$WORK/out/deliverfix3.patch"
test -s "$WORK/out/deliverfix3.patch"
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
        "run_name": "factory-deliver-fix3",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "deliverfix3",
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
    out = Path(__file__).with_name("round18c3-deliver-fix-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
