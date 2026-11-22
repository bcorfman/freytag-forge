# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18b-5: fix-plan lint rule `redundant_effect`, found by the first real rehearsal (18b-4). FREE: no model call, no network.

The rehearsal's Sonnet plan added a beat that sets a fact an earlier beat already sets, with no guard in `when`;
Codex applied it and the standing pacing test failed twice (542 s, 112k tokens wasted). The lint must refuse it first.
One Codex task. Usage: build_round18b5_redundant_effect_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-redundant-effect"

OWNED = [
    "factory/stations/fix_plan.py",
    "factory/stations/planner.py",
    "tests/test_factory_fix_plan.py",
    "tests/test_factory_planner.py",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`, not any API), NEVER use the network, NEVER run a real `ringer.py`, npm, playwright or the bench. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/fix_plan.py` lints a planner's story-data fix plan (`lint_plan(plan, ticket_payload, package)` returns rule-labelled problem strings such as `plan.facts ...`). The first real run of the planner produced this lint-clean plan for scene 1A, which the engine's own test then rejected:
{"kind": "add_pacing_beat", "scene": "1A", "ticket_id": "t", "version": 1, "evidence_keys": ["<any failing-turn key in the payload>"], "reason": "A reminder points her back to the drawer.", "beat": {"id": "drawer_gap_recalled_1a", "at_turn": 12, "sets": {"drawer_gap_pointed_out": true}, "when": {"memory_card_recovered": false, "patrol_in_house": false}, "trailing": true, "verbatim": true, "text": "The street is quiet again. Kristin's eyes go back to the workstation drawer, riding high in its frame, with that thin gap under its lower edge. The officer was too interested in it. Michelle may have left something there."}}
Why it fails: the fact `drawer_gap_pointed_out` is already set true by the existing beat `reyes_rams_drawer_1a` (turn 8), and the pacing test `test_pressure_event_fires_at_its_turn_when_its_conditions_hold` in `tests/test_game_path_completion.py` requires that a beat's effect is NOT already true just before the beat's turn. The existing beat avoids this by guarding itself: its `when` pins `drawer_gap_pointed_out: false`. Other beats avoid it by setting a fact nobody else sets.

BUILD, in `factory/stations/fix_plan.py`, one new lint rule for `add_pacing_beat` plans, label `plan.redundant_effect`: for every fact in `beat["sets"]` with value V, look up `producers(package, fact_id, V)` (from `storygame/story_package/dependencies.py`; read it first). If it returns any producer, and `beat["when"]` does not pin that same fact to the opposite value (`not V`), add one problem: `plan.redundant_effect beat sets <fact_id>, which <producer.description> already sets; guard when with <fact_id>: <not V> or set a fact nothing else sets`. One problem per offending fact, in sorted fact order, producer description of the first producer only. Keep the existing rules and messages unchanged and keep the module story-agnostic (no character names, fact ids or scene ids in the code). Keep the lint a pure function of its inputs.

BUILD, in `factory/stations/planner.py`, one sentence added to `PLANNER_BRIEF` (12th grade reading level, one idea per sentence): a beat must not set a fact that another beat or claim already sets, unless its when guard pins that fact to the opposite value. Do not change anything else in the planner.

TESTS in `tests/test_factory_fix_plan.py` (hermetic, on the real default story package the file already loads): (a) the plan above, with `evidence_keys` and `ticket_id` filled from a valid payload the way the existing tests build one, is rejected with exactly one `plan.redundant_effect` problem naming `drawer_gap_pointed_out` and `reyes_rams_drawer_1a` and no other problem; (b) the same plan with `"drawer_gap_pointed_out": false` added to `when` has no `plan.redundant_effect` problem; (c) a plan whose `sets` names a declared fact that `producers` finds no producer for has no such problem (choose that fact programmatically from the package, do not hard-code an id); (d) a plan that sets a fact to the opposite value of what an existing producer sets (producers returns nothing for it) is not flagged. In `tests/test_factory_planner.py` add one test that `PLANNER_BRIEF` mentions the rule (check a stable key phrase from your sentence). The test files must still run in under 15 seconds each.

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit story data, `storygame/`, `factory/config/`, `factory/stations/wiring.py` or any other test. Write NOTES_18B5.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF @ALLOW_ARGS@ || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity|reyes" factory/stations/fix_plan.py; then echo "story-specific word in fix_plan.py"; exit 1; fi
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_fix_plan.py tests/test_factory_planner.py tests/test_factory_wiring.py tests/test_factory_stations.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || { echo "over the 120 s budget"; exit 1; }
# the real rehearsal plan must now be refused with exactly the new rule
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from factory.stations.fix_plan import lint_plan
from storygame.story_package.loader import load_story_package
package = load_story_package(Path("data/stories/continuity-initiative"))
plan = {"kind": "add_pacing_beat", "scene": "1A", "ticket_id": "t", "version": 1, "evidence_keys": ["k"], "reason": "A reminder points her back to the drawer.",
        "beat": {"id": "drawer_gap_recalled_1a", "at_turn": 12, "sets": {"drawer_gap_pointed_out": True}, "when": {"memory_card_recovered": False, "patrol_in_house": False}, "trailing": True, "verbatim": True,
                 "text": "The street is quiet again. Her eyes go back to the workstation drawer, riding high in its frame, with that thin gap under its lower edge. The officer was too interested in it. Someone may have left something there."}}
payload = {"scene": "1A", "failing_turns": [{"key": "k", "player_input": "x", "candidates_offered": []}]}
problems = lint_plan(plan, payload, package)
print(problems)
assert [p for p in problems if p.startswith("plan.redundant_effect")], "rule did not fire"
PY
.venv/bin/python -m ruff check factory/stations tests/test_factory_fix_plan.py tests/test_factory_planner.py
.venv/bin/python -m ruff format --check factory/stations tests/test_factory_fix_plan.py tests/test_factory_planner.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/redundant-effect.patch"
test -s "$WORK/out/redundant-effect.patch"
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
        "run_name": "factory-redundant-effect",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "lint",
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
                "verified": "lint refuses a beat that sets an already-produced fact unless its when pins the opposite value; the rehearsal's real plan is now refused; brief mentions the rule; module story-agnostic.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18b5-redundant-effect-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
