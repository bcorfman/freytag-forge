# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19p: the probe cost projection counted every run's turns once per run. FREE to build.

One Codex task. Usage: build_round19p_probe_projection_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-probe-projection"
OWNED = ["factory/stations/probe.py", "tests/test_factory_probe.py"]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run `python -m bench run`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`. Tests must be hermetic (no model call, no network, never write factory/state/). Do not add a new test file. If an OLD test pins behaviour this change deliberately changes, update that test to the new behaviour (say so in NOTES.txt); do not leave a failing test and do not weaken an unrelated test.

BACKGROUND. `projected_cost_usd(runs, replicates, rules)` in `factory/stations/probe.py` estimates the billed cost of a probe before it runs. It returns `2 * len(runs) * replicates * sum(len(run["inputs"]) for run in runs) * estimated_usd_per_turn`. That counts every run's turns `len(runs)` times. The handler plays each run once per arm: for each run and each arm it calls the bench with `--replicates <replicates>` on that run's script alone, so the real number of narrated turns is `2 arms * replicates * sum(len(inputs))`. For three runs of 16, 13 and 15 turns at 3 replicates the old formula says 3x too much (1.188 USD instead of 0.396 at 0.0015 USD per turn). The owner keeps estimates against actual cost to improve them, so the estimate must be right.

CHANGE. Fix the formula to `2 * replicates * total_turns * estimated_usd_per_turn` where total_turns is the sum of `len(run.get("inputs", ()))`. Do not change `estimated_usd_per_turn` or any config file. Keep the function signature and return type. The handler already passes the projected value to the ledger `estimate_usd` field; keep that.

TESTS (tests/test_factory_probe.py; hermetic and fast). Add or update: (1) a unit test of `projected_cost_usd` with three runs of 16, 13 and 15 inputs, 3 replicates and rate 0.0015 giving 0.396 (use pytest.approx); (2) one run of 10 inputs at 1 replicate gives 2 * 10 * rate; (3) empty runs give 0; (4) the existing budget-gate test that depends on the projection (the one that refuses when the projected cost is above the remaining budget) must still test the gate: if it relied on the old 3x number, change its inputs so it still crosses the limit under the new formula and say so in NOTES.txt; (5) the handler's ledger row `estimate_usd` equals the corrected projection for a hermetic run with several runs. If an old test pins the old projected value, update it to the new value and say so in NOTES.txt.

HARD LIMITS. Edit only: factory/stations/probe.py and tests/test_factory_probe.py. NEVER edit factory/config/*, guard.py, line.py, live_playtest.py, bench/, story data under data/ or storygame/. Write NOTES.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '^(factory/stations/probe\\.py|tests/test_factory_probe\\.py)$' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git status --porcelain -- data | grep . && { echo "story data changed"; exit 1; } || true
.venv/bin/python - <<'PYV'
from factory.stations.probe import PROBE_RULES, projected_cost_usd

runs = [{"inputs": [0] * n} for n in (16, 13, 15)]
got = projected_cost_usd(runs, 3, {**PROBE_RULES, "estimated_usd_per_turn": 0.0015})
assert abs(got - 0.396) < 1e-9, got
assert projected_cost_usd([], 3, dict(PROBE_RULES)) == 0
print("projection ok", got)
PYV
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_probe.py tests/test_factory_probe_routing.py tests/test_factory_line.py
took=$(( $(date +%s) - start ))
echo "probe tests took $took s (budget 90 s)"
[ "$took" -le 90 ] || { echo "over the 90 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/stations/probe.py tests/test_factory_probe.py
.venv/bin/python -m ruff format --check factory/stations/probe.py tests/test_factory_probe.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/probe-projection.patch"
test -s "$WORK/out/probe-projection.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@REPO@", REPO).replace("@WORK@", WORK)

    return {
        "run_name": "factory-probe-projection",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "probe-projection",
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
                "verified": "The probe's projected cost counts each run's turns once per arm and replicate, so the ledger estimate matches the work done.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round19p-probe-projection-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
