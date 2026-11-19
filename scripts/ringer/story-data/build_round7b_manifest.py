# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 7b: tests that delete records must also drop them from the scene `order` lists (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round7b"
R7_PATCH = "/home/bcorfman/dev/ringer-work/story-data-round7/r7-scene-order.patch"
KEY = "r7b-order-test-helpers"
OWNED = ["tests/test_incident_loader.py", "tests/test_branch_report.py"]

SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run, in this order: [ -e .venv ] || ln -s "
    + REPO
    + " /.venv .venv".replace(" /", "/")
    + " ; git apply "
    + R7_PATCH
    + """ (this brings in round 7, which adds a scene-file key `order`; the patch is NOT yours to edit or undo). Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes).

BACKGROUND. The story source lives in `data/stories/continuity-initiative/source/scenes/<id>.yaml`. Round 7 added an optional top-level `order` key to a scene file: a mapping whose keys `storylets`, `deliveries`, `knowledge` and `pacing_events` each list ids of that scene's records, recording the order the compiled package must keep (read `.plans/story-data-schema-contract.md`, the new subsection about `order`, and `storygame/story_source/l2_order.py`). The check `L2.order_id` rejects an id in `order` that is not a record of that kind in that scene. Several tests copy the real source tree, delete a record from the copy to test a rejection or a report, and then compile or report. Since the copy's `order` list still names the deleted record, compile now fails first with `L2.order_id`, hiding the error or report the test is about.

THE FAILURES (reproduce with the pytest command above):
- tests/test_branch_report.py::test_branch_without_trigger_is_reported_as_dead_end_and_clean_variant (deletes delivery `committed_to_transmit` from scenes/2C.yaml and 2C.match.yaml; error: `unknown deliveries order ID 'committed_to_transmit'`).
- tests/test_incident_loader.py::test_incident_rejections_include_incident_and_offending_id for the cases `recovery has no extra fact` and `recovery awards both outcomes` (they remove claim `k_sl_2c_e_route_effects` via `_remove_match_claim`; error: `unknown knowledge order ID 'k_sl_2c_e_route_effects'`).

YOUR JOB. Fix the TESTS, not the product: where a test helper removes a record (claim, delivery, storylet, pacing event) from a copied source tree, make the helper also remove that id from the same scene's `order` lists (and drop an `order` list or the whole `order` key if it becomes empty, matching how the converter would not write an empty list). Put the pruning in the shared helper the tests already use for removing (`_remove_match_claim`, the `_edit_source` callers) so every deletion path is covered, not only the three failing cases; read both files fully and also check every other place in these two files that deletes or renames a record id. Never make the product accept stale ids; never edit anything under storygame/, data/ or .plans/; never weaken an assertion; the expected error text each test checks must still be the one it checks today. Do not edit tests/story_source or tests/shard_durations.json.

DONE WHEN the whole of tests/test_incident_loader.py and tests/test_branch_report.py passes, ruff is clean on them, and only those two files changed beyond the round 7 patch. If a failure needs more than test edits, write why in NOTES_r7b.txt (worktree root, never committed) and leave it failing.
"""
)


def check() -> str:
    keep = " ".join(f"-e '^{p}$'" for p in OWNED)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_incident_loader.py tests/test_branch_report.py tests/story_source 2>&1 | tail -15
.venv/bin/python -m ruff check tests/test_incident_loader.py tests/test_branch_report.py
.venv/bin/python -m ruff format --check tests/test_incident_loader.py tests/test_branch_report.py
git add -A -- storygame tests data .plans
git apply --numstat {R7_PATCH} | cut -f3 | sort -u > /tmp/r7b_round7_names.txt
bad=$(git diff --cached --name-only | grep -v -x -f /tmp/r7b_round7_names.txt | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached -- {" ".join(OWNED)} > {WORK}/{KEY}.patch
test -s {WORK}/{KEY}.patch
"""


manifest = {
    "run_name": "story-data-round7b",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": KEY,
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 1200,
            "ownership": OWNED,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "the three tests pass because their helpers prune deleted ids from order lists; product code untouched; only the two owned test files changed beyond the round 7 patch.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round7b-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
