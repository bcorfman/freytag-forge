# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 17a: a boolean fact set to false must retract its true twin (and the reverse). FREE: no model call, no network.

Found by reading the round 15d scene 1A report (artifacts/e2e-blind-player.json, replicate 0, turns 11-14): after the
patrol-leaves pacing event asserts patrol_in_house=false, the earlier patrol_in_house=true is still in the FactStore, so
k_sl_1a_b_r0 (needs false) and k_sl_1a_b_r0w (needs true) are both eligible. Their earn_when sentences are identical, so
the semantic matcher can say yes to both, and `_semantic_authored_handoff` refuses when len(matched) != 1.
One Codex task. Usage: build_round17a_boolean_twin_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/1a-boolean-twin"

OWNED = [
    "storygame/runtime/facts.py",
    "tests/test_fact_store_index.py",
    "tests/test_1a_witnessed_recovery.py",
    "tests/test_game_path_completion.py",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run npm, playwright or the bench. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 8 <test files>`.

THE DEFECT (proven, read-only). `FactStore.assert_fact` in `storygame/runtime/facts.py` just adds the fact to a set. A story fact that flips (a pacing event asserts `patrol_in_house` true at turn 7 and false at turn 10, see `data/stories/continuity-initiative/source/scenes/1A.yaml`, pacing events `patrol_enters_1a` and `patrol_leaves_1a`) therefore holds BOTH `Fact(predicate="patrol_in_house", subject="story", value="true")` and `value="false"`. `predicate_matches` in `storygame/runtime/validation.py` answers `any(...)` over matching facts, so after the patrol leaves, a reveal that requires `patrol_in_house: true` (`k_sl_1a_b_r0w`) and its twin that requires `false` (`k_sl_1a_b_r0`) are BOTH eligible (`storygame/runtime/reveal_eligibility.py`). In live play the semantic matcher then matches both (their earn_when sentences are identical) and the engine refuses the player's command, so a player who searches beneath the drawer is told nothing and never gets the memory card. Facts are the single mutable truth; a boolean cannot be both true and false.

BUILD. In `FactStore.assert_fact`, when the fact's `value` is the string "true" or "false", first retract the fact with the same `predicate` and `subject` and the opposite value ("false" or "true") if it is present, then add the new one. Use the existing `retract_fact`/set machinery so the predicate index, the version counter and the guard cache stay correct (read how `asserted` and `_by_predicate` are kept in sync before you edit; do not bypass them). Do not touch facts whose value is not exactly "true" or "false", and never retract a fact with a different subject or predicate. Do not change `retract_fact`, `matching` or `predicate_matches`. Keep it to the smallest correct change. If `Fact` has other identifying fields (for example an object), read the class and retract only the fact that differs from the new one by value alone.

TESTS. (a) In `tests/test_fact_store_index.py` add focused tests: asserting true then false leaves only the false fact, and the index (`matching`) and `version` reflect it; the reverse; asserting the same value twice is idempotent; a non-boolean value is untouched; two subjects do not affect each other; a clone/model_copy of a store keeps working. (b) In `tests/test_1a_witnessed_recovery.py` add a regression using the real default story (follow how that file builds a 1A state): with storylet `SL-1A-E` active, assert `patrol_in_house` true then false the way the engine does for the patrol-leaves event, and check with `storygame.runtime.reveal_eligibility.explain_reveal(state, "player", item)` that `k_sl_1a_b_r0` is eligible and `k_sl_1a_b_r0w` is not (and the reverse while the patrol is in the house). Then run the real engine path if the file already has a helper for advancing turns to the patrol events, and assert the same after turn 10. New tests must run in under 10 seconds in total and use no model.

HARD LIMITS. Edit only the four files above. Never edit story data, `validation.py`, `engine.py`, `state.py`, `reveal_eligibility.py`, `factory/`, `worker/`, `bench/` or `tests/shard_durations.json`. Add no test file. ONE KNOWN TEST MUST CHANGE: `tests/test_game_path_completion.py::test_pressure_event_with_missing_conditions_waits_then_fires_once_they_arrive[kristin_steadies_1a]`. That event (`when: michelle_abduction_suspicion false`, effect `michelle_abduction_suspicion` true) fires on the first activation because an absent fact counts as false; the test's `_satisfy` then asserts the `false` condition again and its last assertion expects BOTH values to coexist, which was the defect. Edit only that test (not `_satisfy`, `_has_value` or other tests): after `_satisfy`, assert each effect's value only for effects whose fact is not re-asserted with the opposite value by `event.when` (the later condition fact now correctly replaces it), and keep asserting `event.id in state.fired_event_ids`. Run the whole file `tests/test_game_path_completion.py` to confirm every other case is unchanged. If any OTHER existing test fails because it relied on both values coexisting, STOP and describe it in the notes instead of editing it. Write NOTES_17A.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -vxF -e storygame/runtime/facts.py -e tests/test_fact_store_index.py -e tests/test_1a_witnessed_recovery.py -e tests/test_game_path_completion.py || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
probe="$WORK/out/probe.out"
.venv/bin/python - > "$probe" 2>&1 <<'PY' || true
from bench.core import default_variation, package_and_state
from storygame.runtime.facts import Fact
from storygame.runtime.reveal_eligibility import explain_reveal
pkg, state = package_and_state(default_variation(), "1A")
items = {k.id: k for k in pkg.knowledge.knowledge if k.id in ("k_sl_1a_b_r0", "k_sl_1a_b_r0w")}
state.active_event_ids.add("SL-1A-E")
def elig():
    return {i: explain_reveal(state, "player", items[i]).eligible for i in items}
assert elig() == {"k_sl_1a_b_r0": True, "k_sl_1a_b_r0w": False}, elig()
state.facts.assert_fact(Fact(predicate="patrol_in_house", subject="story", value="true"))
assert elig() == {"k_sl_1a_b_r0": False, "k_sl_1a_b_r0w": True}, elig()
state.facts.assert_fact(Fact(predicate="patrol_in_house", subject="story", value="false"))
assert elig() == {"k_sl_1a_b_r0": True, "k_sl_1a_b_r0w": False}, ("after the patrol left", elig())
assert [f.value for f in state.facts.matching("patrol_in_house")] == ["false"]
print("probe ok")
PY
cat "$probe"
grep -q "probe ok" "$probe" || { echo "probe failed (this probe fails on the unfixed code on purpose)"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_fact_store_index.py tests/test_reveal_eligibility.py tests/test_1a_*.py tests/test_game_path_completion.py tests/test_incident_engine.py tests/test_world_model.py tests/test_semantic_reveal_match.py tests/test_delivery_variants.py tests/test_reveal_reach.py tests/test_attempt_bundle.py
took=$(( $(date +%s) - start ))
echo "focused suite took $took s (baseline 23 s, budget 90 s)"
[ "$took" -le 90 ] || { echo "focused suite over the 90 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python scripts/quick_suite.py --also tests/test_trailing_pacing_events.py tests/test_recovery_after_choice.py tests/test_gap_rules.py
took=$(( $(date +%s) - start ))
echo "quick suite took $took s (baseline 157 s, budget 450 s)"
[ "$took" -le 450 ] || { echo "quick suite over the 450 s budget"; exit 1; }
.venv/bin/python -m ruff check storygame/runtime/facts.py tests/test_fact_store_index.py tests/test_1a_witnessed_recovery.py tests/test_game_path_completion.py
.venv/bin/python -m ruff format --check storygame/runtime/facts.py tests/test_fact_store_index.py tests/test_1a_witnessed_recovery.py
git diff --cached > "$WORK/out/boolean-twin.patch"
test -s "$WORK/out/boolean-twin.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@REPO@", REPO).replace("@WORK@", WORK)

    return {
        "run_name": "1a-boolean-twin",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "fact-store-twin",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "Asserting a boolean fact retracts its opposite; after the 1A patrol leaves only k_sl_1a_b_r0 is eligible; focused suite green in under 90 s; ruff clean; four files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round17a-boolean-twin-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
