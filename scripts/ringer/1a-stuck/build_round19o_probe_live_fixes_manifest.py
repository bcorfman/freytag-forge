# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19o: three defects the first live probe found (false quota sleep, unmeasured spend, canon judge on a compiled story). FREE to build.

One Codex task. Usage: build_round19o_probe_live_fixes_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-probe-live-fixes"
OWNED = [
    "factory/stations/probe.py",
    "bench/cli.py",
    "bench/core.py",
    "tests/test_factory_probe.py",
    "tests/test_bench.py",
]

COMMON = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run `python -m bench run`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`. Tests must be hermetic (no model call, no network, never write factory/state/). Do not add a new test file: add tests to the owned existing test files. If an OLD test pins behaviour this change deliberately changes, update that test to the new behaviour (say so in NOTES.txt); do not leave a failing test and do not weaken a test that is unrelated to the change."""

SPEC = (
    COMMON
    + """

BACKGROUND. Station 12 of the dark factory (`factory/stations/probe.py`, `probe_handler`) replays the typed commands of saved 1A runs through the bench (`python -m bench run --variation ... --confirm`, run by `default_runner`) once with the old story package (control) and once with the fixed one (candidate), then compares stuck-turn rates. Its first real billed run found three defects. The control arm played all 16 turns of 3 replicates fine and was billed, and then the station put the ticket to sleep until midnight and never judged anything.

DEFECT 1 (false quota sleep). `_raise_probe_quota(text, now)` raises `LimitSleep("cloudflare", next midnight)` as soon as the word QUOTA appears anywhere in the bench output. `bench/cli.py` prints a JSON summary that ALWAYS contains the key `"quota"` (value `null` when nothing happened; see around line 624 of bench/cli.py), so every real run sleeps. Fix: sleep only for a real signal: (a) the markers the sibling helper `_raise_quota` in `factory/stations/live_playtest.py` already recognises (it raises by itself; keep calling it), or (b) a `quota` key with a NON-null value in the printed summary (an object); a `quota: null`, or the word in prose or in a key name alone, must NOT sleep. Read how bench/cli.py prints the summary and what a real quota summary looks like (the `quota` dict built near line 450) and write the rule so a real quota hit still sleeps; keep the old test that feeds a quota output working by giving it a realistic quota summary if it relied on the bare word.

DEFECT 2 (unmeasured spend). The handler records the Worker's spend as the difference of two budget readings (`read_budget`, default `read_worker_budget`, which returns None when the environment variables CLOUDFLARE_WORKER_URL and CLOUDFLARE_WORKER_TOKEN are not set). With no reading the run was billed but the ledger row has `usd: null`, `cost_kind: "unknown"`, so cost cannot be compared with the estimate. Fix: BEFORE any lock file, variation file or bench call, read the budget once with `_safe_budget_read(budget_reader)`; when it returns None, return `StationResult(False, "probe", "cannot read the Worker budget: set CLOUDFLARE_WORKER_URL and CLOUDFLARE_WORKER_TOKEN", tokens=0)` and run nothing. Reuse that first reading as the `before` reading instead of reading twice. The saved-result shortcut (a probe.json that already matches the input hash returns without any run) must keep working WITHOUT a budget reading, so put the new gate after that shortcut. Update the existing tests that pass `read_budget=lambda: None` and expect a run to happen so they pass a valid reading (a dict like the ones other tests in the file use), and add one test that an unreadable budget refuses before the runner is called.

DEFECT 3 (the bench judge cannot read the compiled story). `bench run` always runs the canon judge (`run_judges` in bench/core.py, called in bench/cli.py around line 484), which reads `plot.md`, `storylets.md`, `storylet-routes.yaml`, `pacing.yaml` and `world.yaml` from the story package folder. The default story is now a compiled source tree with none of those files, so the judge fails with ENOENT, every replicate is marked failed and the exit code is 2, although the probe needs only the turn records. Fix: in `bench/cli.py` honour a new boolean variation key `canon_judge` (default true, so every existing variation behaves exactly as before). When it is false, do not call `run_judges` at all: use `{"judgments": [], "judge_calls": 0}`, do not treat completed runs as failed because they have no judgment, and keep everything else (turn-records.json, all-turn-records.json, summary) as it is for runs that completed. Find where variation keys are validated or listed in bench/core.py (an unknown key may be rejected) and add the new key there in the same style as `continuity_judge` and `fact_tracking_judge`. In `factory/stations/probe.py`, `build_variation` must set `"canon_judge": False`.

TESTS. Hermetic, no model call, no network, never write factory/state/. (1) tests/test_factory_probe.py: quota null summary does not sleep; a non-null quota summary sleeps; each marker from `_raise_quota` still sleeps; unreadable budget refuses before the runner; the saved-result shortcut works without a budget reading; `build_variation` has `canon_judge` False. (2) tests/test_bench.py (follow how existing tests there drive `bench run` with a fake runtime and monkeypatched judges; find them with grep for run_judges): with `canon_judge: false` the canon judge is not called, completed runs stay ok, the exit code is 0, and turn-records.json holds the completed runs; with the key absent the canon judge is still called (existing behaviour). If an old test pins behaviour this change deliberately changes, update it and say so in NOTES.txt.

HARD LIMITS. Edit only: factory/stations/probe.py, bench/cli.py, bench/core.py (only for the variation key), tests/test_factory_probe.py, tests/test_bench.py. NEVER edit live_playtest.py, line.py, guard.py, wiring.py, fix_plan.py, planner.py, factory/config/*, story data under data/, storygame/, or the .mjs judge files. Write NOTES.txt (worktree root, never committed) listing every ambiguity and your choice."""
)

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests bench
bad=$(git diff --cached --name-only | grep -vE '^(factory/stations/probe\\.py|bench/cli\\.py|bench/core\\.py|tests/test_factory_probe\\.py|tests/test_bench\\.py)$' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git status --porcelain -- data | grep . && { echo "story data changed"; exit 1; } || true
grep -q "canon_judge" bench/cli.py || { echo "canon_judge not honoured in bench/cli.py"; exit 1; }
grep -q "canon_judge" factory/stations/probe.py || { echo "probe does not set canon_judge"; exit 1; }
grep -q "cannot read the Worker budget" factory/stations/probe.py || { echo "budget gate missing"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_probe.py tests/test_bench.py tests/test_factory_probe_routing.py tests/test_factory_live_playtest.py tests/test_factory_line.py
took=$(( $(date +%s) - start ))
echo "probe and bench tests took $took s (budget 180 s)"
[ "$took" -le 180 ] || { echo "over the 180 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/stations/probe.py bench/cli.py bench/core.py tests/test_factory_probe.py tests/test_bench.py
.venv/bin/python -m ruff format --check factory/stations/probe.py bench/cli.py bench/core.py tests/test_factory_probe.py tests/test_bench.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/probe-live-fixes.patch"
test -s "$WORK/out/probe-live-fixes.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@REPO@", REPO).replace("@WORK@", WORK)

    return {
        "run_name": "factory-probe-live-fixes",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "probe-live-fixes",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "A real probe run no longer sleeps on a null quota, refuses to bill when the Worker budget cannot be read, and skips the canon judge that cannot read a compiled story.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round19o-probe-live-fixes-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
