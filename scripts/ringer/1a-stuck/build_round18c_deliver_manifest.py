# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18c: station 9, deliver and merge. FREE: no model call, no network, no real gh or git push in tests.

One Codex task. Usage: build_round18c_deliver_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-deliver"

OWNED = [
    "factory/stations/deliver.py",
    "factory/stations/__init__.py",
    "factory/stations/live_playtest.py",
    "factory/line.py",
    "factory/followups.py",
    "tests/test_factory_deliver.py",
    "tests/test_factory_line.py",
    "tests/test_factory_followups.py",
    "tests/test_factory_stations.py",
    "tests/test_factory_live_playtest.py",
    "tests/shard_durations.json",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run a real `gh`, never `git push` anywhere real, NEVER run a real `ringer.py`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The factory (package `factory/`) moves persisted tickets through fixed stations (`factory/tickets.py` `Station`). Station 4 (`factory/stations/wiring.py`) makes a fix in a per-ticket git worktree (found with `factory/stations/tree.py` `ticket_tree(payload, ticket_id, root)`), stations 5 and 6 check it on that tree, and station 7 (`factory/stations/live_playtest.py`) plays the scene LIVE against staging, which only runs the code of the merged `main` SHA. Station 9 (`Station.DELIVER`) does not exist yet. Owner decision: the factory merges ITS OWN ticket-generated fix PRs to `main` once the free gates and CI pass; hand-built PRs are never merged by the factory. Read `factory/line.py`, `factory/followups.py`, `factory/stations/wiring.py`, `factory/stations/free_gates.py`, `factory/stations/live_playtest.py`, `factory/guard.py` (`LimitSleep`) and `factory/frozen.py` first. The factory is story-agnostic: no story, character or scene name may appear in the new module.

BUILD `factory/stations/deliver.py` with `deliver_handler(root=None, *, runner=None, gates=None, fetch_version=None, now_fn=None)` returning a `StationHandler`. Every external effect goes through the injectable `runner(argv: list[str], cwd: Path) -> tuple[int, str]` (default: `subprocess.run`, 120 s timeout, stdout and stderr together) so tests use a stub for `gh` and a REAL local temp git repo plus a local bare repo as `origin` for `git`. `gates` is a StationHandler (default `free_gates_handler(root)`). `fetch_version(url) -> dict` defaults to the one station 7 uses (reuse it; do not copy it). The handler, in order:
 1. Refuses (`StationResult(False, "deliver", <reason>)`, no side effect) unless `ticket.payload.get("merge_to_main") is True` (only factory-made tickets merge) and `ticket_tree(...)` finds the tree. Refuses when the tree's diff against `origin/main` is empty, or touches a path matched by `factory.frozen` (patterns from `factory/config/frozen.json`; use `load_patterns` and `touches_frozen`) or any path under `factory/`, `.github/` or `scripts/`.
 2. Idempotency: a delivery record `<workspace>/<ticket id>/delivery.json` (workspace is `ticket.payload["workspace"]`; write atomically) holds `diff_hash` (sha256 of the tree's diff against `origin/main`, including untracked files), `branch` (`factory/<safe ticket id>`), `pr_number`, `merged_sha`, `merged_at`. The record is the idempotency key: a restart or a rerun resumes at the first step not yet recorded and NEVER opens a second PR (also look for an existing PR of that branch with `gh pr list --head <branch> --state all --json number,state`) and NEVER merges twice. A record whose `diff_hash` differs from the tree's current diff is stale: fail with the reason `diff changed after delivery started`.
 3. Never past a failing gate: run `gates(ticket, now)` on the ticket first (it already uses the ticket tree); when it does not pass, return its result as a failure (`check` "deliver", output starting `free gates failed:`), with no push.
 4. Never during a staged run: if the lock file `factory/state/staged_run.lock` (under `root`) exists, or `gh run list --branch main --workflow tests --status in_progress --json databaseId` is non-empty, raise `LimitSleep("staging", now + 600 s)` (a wait is not a failure). The same check runs again immediately before the merge call.
 5. Branch and PR: in the tree, `git fetch origin main`; if the tree's base is behind `origin/main`, rebase onto it (a conflict is a failure with the git output). Create the branch, commit ONLY the diff files (stage by explicit path, never `git add -A`) with message `Factory: <scene> <class> fix (<ticket id>)`, push with `--force-with-lease` to `origin`, and `gh pr create --base main --head <branch>` with a body that lists the ticket id, the plan's `reason` and `kind` when `payload["plan"]` has them, and the gate output tail. Record `pr_number`.
 6. CI: read `gh pr view <n> --json statusCheckRollup,state`. Any check still pending: `LimitSleep("ci", now + 120 s)`. Any check failed or cancelled: fail with the failing check names only (verdicts, no logs). Pass only when every check concluded success and there is at least one check.
 7. Merge: `gh pr merge <n> --merge --delete-branch` (a merge commit, NEVER squash or rebase merge), then read the merge commit SHA with `gh pr view <n> --json mergeCommit,state`; record `merged_sha` and `merged_at`. State `MERGED` already recorded means skip. Then in the main repo clone nothing is touched: prune only with `git -C <tree> fetch --prune origin` and delete the local branch with `git -C <tree> branch -D` only if it exists (ignore its failure).
 8. Wait for the SHA-bound staging deploy: the version URL is `os.environ.get("E2E_API_BASE_URL", "").rstrip("/") + "/api/v1/version"`; the deploy is done when `channel == "staging"`, `runtime == "scene-v1"` and `sha == merged_sha`. Not yet: `LimitSleep("staging", now + 120 s)` until 45 minutes after `merged_at`, then fail with reason `staging did not reach <sha> in 45 minutes`.
 9. Pass with `StationResult(True, "deliver", <one-line summary>, payload_updates={"merged_sha": ..., "expected_sha": ..., "pr_number": ...})`.
Output strings use verdicts only: no raw `gh` JSON beyond the fields above, and no values from the environment or `.env` (never print or log tokens).

CHANGE `factory/line.py`: `StationResult` gains `payload_updates: dict | None = None`. In `step`, on any result with `payload_updates`, merge them into the ticket payload before the station moves. Routing: a ticket whose payload has `merge_to_main` true goes `PROMPT_SNAPSHOT -> DELIVER -> LIVE_PLAYTEST` (instead of 6 -> 7); when it passes station 7 it is DONE (`record_pass`, outcome `delivered`) and does NOT visit station 9 again; a failed station 7 still goes to triage as today. A ticket without `merge_to_main` behaves exactly as today (7 -> 9, and a pass at 9 records the pass). A passed station 9 for a `merge_to_main` ticket moves to station 7 with attempts reset and the updated payload saved; it must not be recorded as delivered.

CHANGE `factory/followups.py`: every ticket `open_followups` creates from triage routing (class tickets, not escalation tickets) carries `"merge_to_main": True` in its payload, EXCEPT parked engine tickets (`needs: engine_plan`). Existing behaviours and ids unchanged.

CHANGE `factory/stations/live_playtest.py`: around the billed runner call only, create `factory/state/staged_run.lock` under the repository root (content: ticket id and an ISO timestamp; make the parent folder if needed) and remove it in a `finally`; a lock that already exists and is less than 6 hours old makes the station return a failure `staged run already in progress` without running; an older lock is replaced. Grading a saved report writes no lock.

CHANGE `factory/stations/__init__.py`: register `Station.DELIVER: deliver_handler(root)`; update the closing comment (stations 0, 1 and 3 remain unbuilt).

TESTS (hermetic; stubs and local temp git repos only; fake `gh` never runs for real). `tests/test_factory_deliver.py` covers: refusal without `merge_to_main`; refusal of an empty diff, of a frozen path and of a path under `factory/`; free gate failure means no push and no `gh pr create`; the staged lock file makes `LimitSleep("staging", ...)` and no side effect; an in-progress `tests` run on main does the same; the full happy path in one process with a local bare origin (branch pushed, PR created once, CI pending raises `LimitSleep("ci", ...)` then success, merge called with `--merge --delete-branch` and never `--squash` or `--rebase`, staging not yet at the SHA raises `LimitSleep("staging", ...)`, then passes and returns the payload updates); a restart after the PR exists (second handler instance, same record) opens no second PR and does not merge twice; a stale record (diff changed) fails; a failed CI check fails with the check names only; the 45-minute deploy timeout fails; no output contains a token-looking value from the environment (set a fake secret in env and assert it never appears). `tests/test_factory_line.py`: the new routing (merge ticket 6 -> 9 -> 7 -> delivered, payload updates stored; non-merge ticket unchanged). `tests/test_factory_followups.py`: `merge_to_main` set on class tickets, not on escalation or parked engine tickets. `tests/test_factory_live_playtest.py`: the lock is created during the runner call and removed after (also when the runner raises), and a fresh lock blocks the run. `tests/test_factory_stations.py`: the registry holds station 9. Each new or changed test file runs in under 20 seconds. After the tests pass run `.venv/bin/python scripts/regen_shard_durations.py --missing-only` so `tests/shard_durations.json` lists `tests/test_factory_deliver.py`.

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit `factory/guard.py`, `factory/frozen.py`, `factory/config/`, `factory/checks/`, `factory/stations/wiring.py`, `factory/stations/planner.py`, story data, `storygame/`, or any other test. Do not write `factory/state/` files from tests except under a temp directory. Write NOTES_18C.txt (worktree root, never committed) listing every ambiguity and your choice."""

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
git diff --cached > "$WORK/out/deliver.patch"
test -s "$WORK/out/deliver.patch"
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
        "run_name": "factory-deliver",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "deliver",
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
    out = Path(__file__).with_name("round18c-deliver-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
