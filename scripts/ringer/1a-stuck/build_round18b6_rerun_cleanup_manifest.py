# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18b-6: two plumbing bugs from the first real rehearsal (18b-4). FREE: no model call, no network.

(1) wiring `_clear_previous` prunes git worktrees before it deletes the previous Ringer folder, so a rerun after a failed
Ringer run dies with "missing but already registered worktree". (2) the generated manifest task has no `verified`
sentence, which Ringer's lint flags. One Codex task. Usage: build_round18b6_rerun_cleanup_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-rerun-cleanup"

OWNED = [
    "factory/stations/wiring.py",
    "factory/manifests.py",
    "tests/test_factory_wiring.py",
    "tests/test_factory_manifests.py",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run a real `ringer.py`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BUG 1, `factory/stations/wiring.py` `_clear_previous`. It runs `git worktree remove --force` on the ticket's `tree`, then `git worktree prune`, and only afterwards deletes `manifest.json`, `plan.json`, `out` and the `ringer` folder. When a previous Ringer run failed, Ringer leaves its own worker worktree registered inside the `ringer` folder (`<ticket_dir>/ringer/<task key>`). Deleting that folder after the prune leaves a stale registration, and the next Ringer run fails at setup with "'<path>' is a missing but already registered worktree; use 'add -f' to override, or 'prune' or 'remove' to clear". Fix: delete the leftover paths first, then run `git worktree prune` last, so a registration whose folder was just deleted is pruned. Keep the error handling and return values as they are.

BUG 2, `factory/manifests.py` `build_manifest`. Ringer's lint says: "wire: no 'verified' description; a reader of the results page sees 'checked' but not what the check proves - add one plain-English sentence." Add an optional `verified: str = ""` field to `TaskSpec` and emit it as the task's `"verified"` key in the manifest when it is non-empty. If it is empty, emit a generic sentence built from the task key and ownership (for example "Checks that <key> changed only the owned files and the repository tests and checks it names pass.") so no manifest from this builder lacks the key. In `factory/stations/wiring.py` pass a specific sentence on the one TaskSpec it builds: the compiled package holds the exact plan text, the story source formats cleanly, and the game-path completion tests pass.

TESTS (hermetic; stubs only). In `tests/test_factory_wiring.py`: reproduce bug 1 with a real throwaway git repository the way the existing rerun test does: create a ticket directory whose `ringer/wire` is a real registered worktree that Ringer would have left behind (use `git worktree add --detach` under the ticket's `ringer` folder), then call the handler's cleanup path (use `_clear_previous` directly or the handler with a stub Ringer) and assert that afterwards `git worktree list` shows no registration for the ticket's ringer folder and a second `git worktree add` at that same path succeeds. The test must fail on today's code. In `tests/test_factory_manifests.py`: a task with `verified` set emits exactly that sentence; a task without it emits a non-empty generic sentence; the manifest still round-trips through JSON. Each test file still runs in under 15 seconds.

HARD LIMITS. Edit only the owned files: @OWNED@. Write NOTES_18B6.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF @ALLOW_ARGS@ || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_wiring.py tests/test_factory_manifests.py tests/test_factory_stations.py tests/test_factory_planner.py tests/test_factory_fix_plan.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || { echo "over the 120 s budget"; exit 1; }
# a generated manifest must carry the verified key and pass Ringer's own lint
.venv/bin/python - <<'PY'
from factory.manifests import TaskSpec, build_manifest, write_manifest
m = build_manifest(run_name="probe", repo="@REPO@", workdir="@WORK@/probe", tasks=[TaskSpec(key="wire", ownership=["factory/__init__.py"], spec_body="probe", check_extra="true")])
assert m["tasks"][0].get("verified"), m["tasks"][0].keys()
write_manifest(m, "@WORK@/out/probe-manifest.json")
PY
lint_out=$(cd ~/dev/ringer && ./ringer.py lint @WORK@/out/probe-manifest.json 2>&1 || true)
echo "$lint_out"
if echo "$lint_out" | grep -q "no 'verified'"; then echo "ringer lint still flags a missing verified"; exit 1; fi
.venv/bin/python -m ruff check factory tests/test_factory_wiring.py tests/test_factory_manifests.py
.venv/bin/python -m ruff format --check factory tests/test_factory_wiring.py tests/test_factory_manifests.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/rerun-cleanup.patch"
test -s "$WORK/out/rerun-cleanup.patch"
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
        "run_name": "factory-rerun-cleanup",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "cleanup",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=medium"],
                "max_attempts": 2,
                "timeout_s": 1800,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "A rerun after a failed Ringer run no longer hits a stale worktree registration, and every generated manifest task carries a verified sentence that Ringer's lint accepts.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18b6-rerun-cleanup-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
