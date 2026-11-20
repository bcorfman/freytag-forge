# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Fix the stale ending predicate behind ~101 nightly journey failures.

Diagnosis (ringer-work/nightly-journey-failures/report.md, proved by re-running the test at
06b2ccb3 and its parent): the 3C rebuild made `evacuation_complete` the ending and the engine
sets `state.story_complete`; `storygame.personas._resolution_complete` still looks for the
removed fact `resolution_complete`, so scripted journeys never see the ending.
One Codex task. Usage: build_nightly_journey_fix_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/nightly-journey-failures"
OWNED = [
    "storygame/personas.py",
    "tests/journey_prefix.py",
    "tests/test_game_path_journeys.py",
    "tests/test_evidence_gap_journeys.py",
]
ENV = "PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp"
NIGHTLY_SECONDS = 600
QUICK_SECONDS = 90  # test_persona_escalation alone spends 57 s in setup on unchanged main (2026-11-20)
QUICK_TESTS = "tests/test_journey_prefix_equivalence.py tests/test_persona_escalation.py tests/test_deadline_world_only_exit.py tests/test_factory_carry_matrix.py"

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network, never pass --cov to pytest. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>`. Run tests as `{ENV} .venv/bin/python -m pytest -q -p no:cacheprovider -n 16 --run-nightly <tests>` (`-n 0` for a single test).

YOU OWN exactly: {", ".join(OWNED)}. Also write NOTES.txt at the worktree root (never committed). Never edit `data/`, `storygame/runtime/`, `storygame/story_package/`, `packages/`, `factory/`, `scripts/` or any other test. Do not change the story or the engine to make a test pass.

THE PROBLEM (already diagnosed and proved). Commit 06b2ccb3 ("Rebuild 3C as a finite evacuation that ends the game") replaced the story's old ending fact `resolution_complete` with a finite 3C evacuation: `evacuation_complete` (declared in `data/stories/continuity-initiative/source/scenes/3C.yaml`) now gates the ending, and the engine sets `RuntimeState.story_complete = True` when the ending fires (`storygame/runtime/engine.py`, search for `story_complete`). The plan `.plans/game-reimagination/phase2-3c-contract.md` (lines 12-15 and 65-88) says Phase Two of 3C is now optional and no longer gates the ending, and that `resolution_complete` has no job after the redesign. But `storygame/personas.py` still defines `_RESOLUTION_FACT = "resolution_complete"` and `_resolution_complete(state)` checks only that fact, and the scripted journeys in `tests/journey_prefix.py`, `tests/test_game_path_journeys.py` and `tests/test_evidence_gap_journeys.py` stop on and assert `_resolution_complete`. On the real story the default scripted journey reaches 3C at turn 48, completes the evacuation, `story_complete` is True, and the test still fails. This breaks the nightly suite (`--run-nightly`): 93 failures in `tests/test_game_path_journeys.py` and 8 in `tests/test_evidence_gap_journeys.py`.

WHAT TO DO.
1. Make `_resolution_complete(state)` in `storygame/personas.py` return True when `state.story_complete` is True, OR when the legacy fact `resolution_complete` is true (some fixture stories and `tests/test_deadline_world_only_exit.py` still end with that fact). The rule must stay story-agnostic: never name `evacuation_complete` or any Continuity Initiative id in `storygame/`. Keep the name `_resolution_complete` and the `"resolution_complete"` key in `run_persona`'s payload (other tests read it). Read every caller (`grep -rn _resolution_complete storygame tests factory scripts`) and confirm each still means "the story has ended".
2. Run both nightly files on the real story. For every test that still fails, find out why with evidence (file:line). Fix the TEST only when the failure is the stale ending model of the old design. Known example: some realization cases prefer an optional Phase-Two 3C storylet realization such as `k_sl_3c_e_r2`; if the ending now fires before that realization can be offered, the old expectation "every player realization lies on an earned route to the ending" no longer fits a realization that, by the new design, belongs after or beside the ending. In that case change the test so that such a realization must still be OFFERED and PICKED on a legal route (it is reachable content), but do not require it to precede the ending; derive which realizations those are from the package (for example from the 3C storylet definitions and their relation to the ending trigger), never from a hard-coded list of ids, and explain the rule in a comment citing the plan. If a realization can no longer be offered at all on any route, do NOT hide it: leave its case failing and report it in NOTES.txt as a possible story defect. Never use xfail, skip, or deselection to make a case pass, and never loosen `forced_exits`, `deadline_events` or `AUTHORED_TURN_BUDGET` checks. If `KNOWN_FORCED_EXITS` or `CHAINS` entries are stale, update them only with evidence.
3. NOTES.txt: the change to `_resolution_complete` and the callers you checked; the before/after counts for both files (run them on unmodified HEAD first and record the counts); for every test you changed, the old expectation, the new one, and why the new design justifies it (file:line); every test that still fails, with its node id on a line starting `STILL FAILING: <node id>` followed by the reason.

BUDGETS (enforced by the check on a 16-core machine): both nightly files together with `-n 16` under {NIGHTLY_SECONDS} s; the quick dependent tests ({QUICK_TESTS}) under {QUICK_SECONDS} s.
"""

CHECK = f"""set -eo pipefail
OUT={WORK}/fix
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A -- storygame tests data packages factory scripts
bad=$(git diff --cached --name-only | grep -vxF {" ".join(f"-e {f}" for f in OWNED)} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
[ -s NOTES.txt ] || {{ echo "missing NOTES.txt"; exit 1; }}
! git diff --cached -U0 -- storygame/personas.py | grep -nE "^\\+.*(evacuation_complete|k_sl_|continuity)" || {{ echo "the patch adds story-specific ids to storygame/personas.py"; exit 1; }}
! git diff --cached -U0 -- tests | grep -nE "^\\+.*(xfail|pytest\\.skip|mark\\.skip|deselect)" || {{ echo "the patch adds xfail/skip/deselect"; exit 1; }}
.venv/bin/python -m ruff check {" ".join(OWNED)}
.venv/bin/python -m ruff format --check {" ".join(OWNED)}
start=$(date +%s.%N)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 16 {QUICK_TESTS}
q=$(echo "$(date +%s.%N) - $start" | bc); echo "quick dependent tests: ${{q}}s (budget {QUICK_SECONDS}s)"
awk -v t="$q" 'BEGIN {{ exit !(t < {QUICK_SECONDS}) }}' || {{ echo "quick tests over budget"; exit 1; }}
# the default journey must pass outright
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 --run-nightly tests/test_game_path_journeys.py::test_the_default_policy_earns_the_whole_chain_without_a_deadline
# both nightly files: every remaining failure must be reported in NOTES.txt
rc=0
start=$(date +%s.%N)
timeout {NIGHTLY_SECONDS + 120} .venv/bin/python -m pytest -q -p no:cacheprovider -n 16 --run-nightly -rf tests/test_game_path_journeys.py tests/test_evidence_gap_journeys.py > "$OUT/nightly.out" 2>&1 || rc=$?
n=$(echo "$(date +%s.%N) - $start" | bc)
tail -40 "$OUT/nightly.out"
echo "nightly files: ${{n}}s (budget {NIGHTLY_SECONDS}s), exit $rc"
[ "$rc" = 0 ] || [ "$rc" = 1 ] || {{ echo "pytest exited $rc"; exit 1; }}
awk -v t="$n" 'BEGIN {{ exit !(t < {NIGHTLY_SECONDS}) }}' || {{ echo "nightly files over budget"; exit 1; }}
.venv/bin/python - "$OUT/nightly.out" <<'PY'
import re, sys
out = open(sys.argv[1]).read()
failed = sorted(set(re.findall(r"^FAILED (\\S+)", out, re.M)))
passed = int((re.search(r"(\\d+) passed", out) or [0, 0])[1])
notes = open("NOTES.txt").read()
reported = set(re.findall(r"^STILL FAILING: *(\\S+)", notes, re.M))
missing = [f for f in failed if f not in reported]
assert not missing, f"failing tests not reported as STILL FAILING in NOTES.txt: {{missing}}"
assert passed >= 90, f"only {{passed}} passed; the ending fix should clear most of the 101 failures"
assert len(failed) <= 10, f"{{len(failed)}} still failing: {{failed}}"
print(f"nightly ok: {{passed}} passed, {{len(failed)}} still failing and reported")
PY
git diff --cached > "$OUT/journey-fix.patch"
cp NOTES.txt "$OUT/NOTES.txt"
test -s "$OUT/journey-fix.patch"
"""


def build() -> dict:
    return {
        "run_name": "nightly-journey-failures",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "journey-fix",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 5400,
                "check_timeout_s": 1200,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": f"Only the four owned files change; personas.py stays story-agnostic; no xfail/skip added; ruff clean; dependent quick tests pass under {QUICK_SECONDS}s; the default journey passes; the two nightly files run under {NIGHTLY_SECONDS}s with at least 90 passing and every remaining failure reported in NOTES.txt.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("nightly-journey-fix-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
