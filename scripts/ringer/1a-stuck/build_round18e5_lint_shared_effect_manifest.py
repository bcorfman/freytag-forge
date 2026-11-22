# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18e-5: lint refuses a beat that sets a fact ANY existing pacing event sets. FREE: no model call.

One Codex task. Usage: build_round18e5_lint_shared_effect_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-lint-shared"
OWNED = ["factory/stations/fix_plan.py", "tests/test_factory_fix_plan.py", "tests/test_factory_wiring.py", "tests/test_factory_planner.py", "tests/test_factory_manifests.py"]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/fix_plan.py` `lint_plan` (read it and `tests/test_factory_fix_plan.py`) checks a planner's fix plan before Codex builds it. Round 18e-4 added `plan.shared_effect` (function `_earlier_pacing_problems`): a beat is refused when an existing pacing event with a LATER turn also sets one of its `sets` facts. A second real run showed that is still not enough. The planner then proposed `drawer_sits_crooked_1a` at turn 11, guarded `when {drawer_gap_pointed_out: false, memory_card_recovered: false, patrol_in_house: false}`, setting `drawer_gap_pointed_out` true, a fact the existing pacing event `reyes_rams_drawer_1a` (turn 8) sets. The engine test `test_pressure_event_fires_at_its_turn_when_its_conditions_hold` (tests/test_game_path_completion.py) failed for the new beat at the turn just before it: `assert _is_true(state, 'drawer_gap_pointed_out') is not True` failed because the fact was already true. So a guard and a later turn do NOT make a shared fact safe. In the real runs the only beat that passed that test set a fact no other pacing event sets (`drawer_opened`).

BUILD. Change the rule in `_earlier_pacing_problems` (rename the function `_shared_effect_problems` and its problem prefix `plan.shared_effect`; keep it called from the same place): for every `sets` fact F and value v of the new beat, EVERY existing pacing event (any `at_turn`, any scene) whose effects set F to v produces a problem, regardless of the beat's turn and regardless of its `when` guard: `plan.shared_effect beat sets {F}, which pacing event {id} (turn {U}) also sets; set a fact no other pacing event sets`. Verdict only; no further explanation. One problem per (fact, event) pair, sorted by (fact, turn, id). Remove the old message and its turn comparison. Keep `plan.redundant_effect` as it is (it still covers producers that are not pacing events) and keep every other rule and message. A fact that no pacing event sets is never refused by this rule.

TESTS in `tests/test_factory_fix_plan.py` (hermetic, real default story package as the file already uses). Replace the three tests the previous round added with these, named exactly: `test_rejects_beat_that_sets_a_fact_any_pacing_event_sets` (the turn-5 plan `{id drawer_gap_noticed_1a, sets {drawer_gap_pointed_out: true}, when {drawer_gap_pointed_out: false, memory_card_recovered: false}}` AND the turn-11 plan above with `patrol_in_house: false` are each refused with a `plan.shared_effect` problem that names `reyes_rams_drawer_1a` and turn 8), `test_shared_effect_is_refused_at_and_after_the_producer_turn_too` (the same plan at turn 8 and at turn 9 is also refused), `test_shared_effect_rule_ignores_a_fact_no_pacing_event_sets` (a plan whose `sets` fact no pacing event sets, at turn 5 and at turn 11, gets no `plan.shared_effect` problem). Fix any other existing test that legitimately changes (the existing `test_redundant_effect_is_allowed_with_opposite_guard` checks only the `plan.redundant_effect` prefix and stays valid). The file runs in under 15 seconds.

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit story data, `storygame/`, `factory/stations/wiring.py`, `factory/stations/planner.py` or any other test. Write NOTES_18E5.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '^(factory/stations/fix_plan\\.py|tests/test_factory_(fix_plan|wiring|planner|manifests)\\.py)$' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
grep -q "plan.shared_effect" factory/stations/fix_plan.py || { echo "rule missing from fix_plan.py"; exit 1; }
for name in test_rejects_beat_that_sets_a_fact_any_pacing_event_sets test_shared_effect_is_refused_at_and_after_the_producer_turn_too test_shared_effect_rule_ignores_a_fact_no_pacing_event_sets; do
  grep -q "def $name" tests/test_factory_fix_plan.py || { echo "test $name missing"; exit 1; }
done
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_fix_plan.py
took=$(( $(date +%s) - start ))
echo "fix plan tests took $took s (budget 15 s)"
[ "$took" -le 15 ] || { echo "over the 15 s budget"; exit 1; }
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/test_factory_planner.py tests/test_factory_wiring.py tests/test_factory_manifests.py
.venv/bin/python -m ruff check factory tests/test_factory_fix_plan.py
.venv/bin/python -m ruff format --check factory tests/test_factory_fix_plan.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/lint-shared.patch"
test -s "$WORK/out/lint-shared.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@REPO@", REPO).replace("@WORK@", WORK).replace("@OWNED@", ", ".join(OWNED))

    return {
        "run_name": "factory-lint-shared",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "lint-shared",
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
                "verified": "Plan lint refuses a beat that sets a fact any existing pacing event sets, whatever its turn or guard, so the planner hears about it before a worker runs; the real turn-5 and turn-11 plans are refused; tests use the real default story only.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18e5-lint-shared-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
