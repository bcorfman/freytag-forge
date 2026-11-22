# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18b-7: a failed wiring check goes back to the planner. FREE: no model call, no network.

The 18b-4 rehearsal showed Codex retrying a plan that no worker can make pass (the pacing test rejected the plan itself).
The wiring station now re-plans with the check output instead. One Codex task. Usage: build_round18b7_replan_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-replan"

OWNED = [
    "factory/stations/wiring.py",
    "factory/stations/planner.py",
    "tests/test_factory_wiring.py",
    "tests/test_factory_planner.py",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run a real `ringer.py`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/wiring.py` `wiring_handler` asks an optional `planner` for a fix plan when the payload has none, lints it, then runs ONE Ringer task (a Codex worker plus a check) in a per-ticket folder and applies the patch to a per-ticket tree. In the first real run the plan was lint-clean but the check (the engine's own tests) rejected the plan itself, and the Codex worker was retried on the same plan, which cannot help: a worker cannot change the plan. The right move is to send the check's output back to the planner and ask for a revised plan.

BUILD in `factory/stations/planner.py`: the planner callable returned by `make_planner` accepts two new optional keyword arguments, `feedback_plan: dict | None = None` and `check_output: str | None = None`, after the existing `(ticket, package, now)`. When given, the FIRST prompt carries the previous plan and the check output; `build_prompt` gains an optional `check_output: str | None = None` and, when set, adds a section headed `Check output (this plan was applied and the check failed):` followed by the text verbatim, placed after the previous plan. Verdicts only: add no explanation of why. Keep every existing behaviour and signature otherwise (lint problems still go back the same way on the planner's own retries). In `PLANNER_BRIEF` add one sentence (12th grade reading level): when a check output is shown, the plan was applied and the check failed, so reply with a revised plan that fixes the reason shown.

BUILD in `factory/stations/wiring.py`: when the plan came from the planner (the payload had no `plan`), run a bounded loop of at most `MAX_REPLANS = 3` rounds (a module constant): round 1 as today; if Ringer fails the check (non-zero exit, or a missing or empty patch) and rounds remain, call `planner(ticket, package, now, feedback_plan=plan, check_output=<the tail of the output, same 4000-character tail the handler already reports>)`, then lint, rewrite `plan.json`, clear the previous attempt (`_clear_previous`) and run Ringer again. Other failures (plan lint, planner returned no plan, workspace, git worktree or patch-apply errors) end the station at once as today. Sum the planner tokens of every call into `StationResult.tokens`. When the rounds run out, fail with the last Ringer output as today. For a plan that came from the payload (no planner use) behave EXACTLY as today: one round, no planner call. Planner-driven rounds use `max_attempts=1` for the Codex task (a plan error is the likely cause; the loop is the retry); payload plans keep `max_attempts=2`. Never mutate `ticket.payload`. Refactor into small helpers so the handler stays readable; keep the existing messages unchanged.

TESTS (hermetic; stubs only, no model, no real Ringer). In `tests/test_factory_wiring.py`: (a) stub planner and stub Ringer that fails the first round (non-zero exit with a recognisable output) and passes the second: the planner is called twice, the second call receives `feedback_plan` equal to the first plan and `check_output` containing the failing output tail, plan.json holds the second plan, the second manifest's task has `max_attempts` 1, the result passes and tokens sum both calls; (b) Ringer fails every round: the station fails after exactly `MAX_REPLANS` Ringer runs and `MAX_REPLANS` planner calls total, with the last output in the result; (c) a payload that carries its own plan and a failing Ringer: one Ringer run, no planner call, `max_attempts` 2; (d) a second-round plan that fails lint ends the station with the lint problems and no further Ringer run. In `tests/test_factory_planner.py`: `build_prompt` with `check_output` contains the section header and the text verbatim after the previous plan, and without it is byte-identical to today's prompt; a stub-`claude` planner call with `feedback_plan` and `check_output` sends them in its first prompt. Each test file still runs in under 15 seconds.

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit `factory/stations/fix_plan.py`, `factory/manifests.py`, story data, `storygame/`, `factory/config/` or any other test. Write NOTES_18B7.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF @ALLOW_ARGS@ || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity|reyes" factory/stations/planner.py; then echo "story-specific word in planner.py"; exit 1; fi
grep -q "MAX_REPLANS" factory/stations/wiring.py || { echo "MAX_REPLANS constant missing"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_wiring.py tests/test_factory_planner.py tests/test_factory_stations.py tests/test_factory_fix_plan.py tests/test_factory_manifests.py tests/test_factory_line.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || { echo "over the 120 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_wiring.py tests/test_factory_planner.py
.venv/bin/python -m ruff format --check factory tests/test_factory_wiring.py tests/test_factory_planner.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/replan.patch"
test -s "$WORK/out/replan.patch"
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
        "run_name": "factory-replan",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "replan",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "When the wiring check fails on a planner-made plan, the station asks the planner for a revised plan with the check output, up to three rounds, and a supplied plan is still tried once with no planner call; tests use stubs only.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18b7-replan-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
