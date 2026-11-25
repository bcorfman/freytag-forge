# ruff: noqa: E501
"""Round 28a: Step 2 free work. Task A strengthens the M4 outcome-contract fixture; task B adds the contract-scene builder
that fills `scene.delivered_before` from earlier scenes. Free, no model."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-28"
FIX = "/home/bcorfman/dev/ringer-work/qual-20261122/qualification/outcome_contract_fixtures"
PY = ".venv/bin/python"

SETUP = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git reset -q
"""


def ownership_guard(owned: list[str]) -> str:
    owned_re = "|".join(p.replace(".", r"\.") for p in owned)
    return f"""git add -A -- factory tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({owned_re})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
"""


LINT = f"""PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
echo "ruff files: $PYFILES"
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
"""

# ---------------------------------------------------------------- task A
OWNED_A = [
    "tests/fixtures/outcome_contract/cases.json",
    "tests/test_outcome_contract.py",
    "factory/outcome_contract.py",
]
SPEC_A = b.COMMON + (
    "You may edit ONLY: tests/fixtures/outcome_contract/cases.json, tests/test_outcome_contract.py and (only if a new case proves a real classifier bug) factory/outcome_contract.py. "
    "Nothing else.\n\n"
    "BACKGROUND. factory/outcome_contract.py::classify_run(run, scene) is the pure outcome classifier; tests/fixtures/outcome_contract/README.md is the contract and cases.json the frozen examples "
    "(read both and tests/test_outcome_contract.py FIRST; the README is read-only). The owner has approved strengthening the example for defect M4 (a timed pressure reveal must not count as the player's progress). "
    "Today the case `timed_reveal_masks_futile_action` uses the input 'Wait by the door.' on every turn. A player who waits is not trying to progress, so the case does not show a futile COMMAND. "
    "The contract's null-grounding rule: a grounding id listed in a turn's `null_grounding_ids` is a pressure event, not progress; a pacing event that fires only because the command changed a fact is the world answering the player, "
    "so its grounding IS progress (it will not be in `null_grounding_ids`, because a replay of the pacing pass on the pre-command state would not fire it).\n\n"
    "DO, TEST FIRST:\n"
    "1. In cases.json change ONLY the `input` and `raw_input` fields (if present) of the three turns of `timed_reveal_masks_futile_action` to one futile named-object command, for example 'Search the filing cabinet.' (the same text on all three turns). Change nothing else in that case: expected results stay the same.\n"
    "2. Add case `pressure_beside_earned_reveal` (tier core): three turns in a scene with pacing_window 3 and candidates offered; turn 2's command matches candidate k_c1 AND a pressure reveal k_pressure fires on the same turn. Turn 2: grounding_ids [k_c1, k_pressure], null_grounding_ids [k_pressure], matched_candidate k_c1, pressure_event true. Expected: turn 2 knowledge_progress true (k_c1 is new and not null grounding) and the run is not confirmed_stuck (follow the README for the exact stall rule and make the expected block say what the classifier must return; turns 1 and 3 are futile no_effect turns).\n"
    "3. Add case `pacing_event_caused_by_command_fact` (tier core): turn 2's command commits a fact (committed_facts non-empty), a pacing event fires on that turn (pressure_event true) and its grounding k_world_answer is NOT in null_grounding_ids (the replay on the pre-command state would not have fired it). Expected: turn 2 knowledge_progress true and the run is not confirmed_stuck.\n"
    "4. Give each new case an `id`, `tier`, `description`, `reason` (one sentence saying which defect or rule it pins), `scene`, `run`, `expected` in exactly the shape of the existing cases (copy the shape of `timed_reveal_masks_futile_action`; every turn carries every field that case's turns carry).\n"
    "5. Update tests/test_outcome_contract.py only where it pins the number of cases or lists case ids (the suite ran 27 cases; it must now run 29, none skipped). Add one explicit test that the three M4-related cases exist and that no turn of `timed_reveal_masks_futile_action` has an input starting with 'Wait'.\n"
    "6. Run the tests. If a new case fails because classify_run is wrong (not because your case is wrong against the README), fix classify_run minimally and say so in NOTES.txt; if the README is ambiguous, pick the reading that keeps all other 27 cases passing and record it in NOTES.txt.\n"
    "Do not modify any other existing case. Do not touch tests/shard_durations.json."
)
CHECK_A = (
    SETUP
    + ownership_guard(OWNED_A)
    + f"""start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs tests/test_outcome_contract.py 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -6
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 60 s)"
[ "$took" -le 60 ] || {{ echo "over the 60 s budget"; exit 1; }}
case "$out" in *skipped*) echo "tests were skipped; every example must run"; exit 1;; esac
{PY} - <<'PYV'
import json
new = json.load(open("tests/fixtures/outcome_contract/cases.json"))
old = json.load(open("{FIX}/cases.json"))
newd = {{c["id"]: c for c in new}}
oldd = {{c["id"]: c for c in old}}
assert len(new) == 29, len(new)
assert set(newd) - set(oldd) == {{"pressure_beside_earned_reveal", "pacing_event_caused_by_command_fact"}}, set(newd) ^ set(oldd)
for cid, c in oldd.items():
    if cid != "timed_reveal_masks_futile_action":
        assert newd[cid] == c, f"existing case changed: {{cid}}"
m4 = json.loads(json.dumps(newd["timed_reveal_masks_futile_action"]))
for t in m4["run"]["turns"]:
    assert not t["input"].lower().startswith("wait"), t["input"]
    t["input"] = "X"
    if "raw_input" in t:
        t["raw_input"] = "X"
o4 = json.loads(json.dumps(oldd["timed_reveal_masks_futile_action"]))
for t in o4["run"]["turns"]:
    t["input"] = "X"
    if "raw_input" in t:
        t["raw_input"] = "X"
assert m4 == o4, "the M4 case changed in more than its inputs"
from factory.outcome_contract import classify_run
for cid in ("pressure_beside_earned_reveal", "pacing_event_caused_by_command_fact"):
    r = classify_run(newd[cid]["run"], newd[cid]["scene"])
    t2 = [t for t in r["turns"] if t["turn"] == 2][0]
    assert t2["knowledge_progress"] is True, (cid, t2)
    assert 2 not in r["confirmed_stuck"], (cid, r["confirmed_stuck"])
print("M4 fixture strengthened as specified")
PYV
"""
    + LINT
    + 'git diff --cached > "$WORK/out/m4-fixture.patch"\ntest -s "$WORK/out/m4-fixture.patch"\n'
)

# ---------------------------------------------------------------- task B
OWNED_B = ["factory/contract_scene.py", "tests/test_contract_scene.py", "tests/shard_durations.json"]
SPEC_B = b.COMMON + (
    "You may edit ONLY: factory/contract_scene.py (new), tests/test_contract_scene.py (new) and tests/shard_durations.json (add exactly one entry for the new test file, same format as its neighbours, value 1.0). Nothing else.\n\n"
    "BACKGROUND. factory/outcome_contract.py::classify_run(run, scene) classifies one replicate of one scene. Its `scene` argument is a dict "
    "{id, pacing_window (int or null), terminal (bool), reveal_ids [str], delivered_before [str], ending_requires [str], non_voiceable_says [str], unlearned_terms [{term, requires}], epilogue_candidates [str]} "
    "(read tests/fixtures/outcome_contract/README.md, factory/outcome_contract.py and its tests FIRST; do NOT edit them). `delivered_before` is the set of knowledge ids the player already has when the scene starts; "
    "classify_run subtracts it from a turn's grounding ids, so a re-grounded old item is not counted as new progress. Nothing builds this `scene` dict from a story package yet, and `delivered_before` is the missing part. "
    "Saved evidence: in a run of scene 2C the narrator re-grounded `k_sl_2b_b_r4` (a scene 2B item) on turn 2, which the contract read as new progress; in scene 2A the entry item `k_scene_2a_entry` and in scene 1B the item `k_sl_1a_b_r1` (scene 1A) were re-grounded the same way.\n\n"
    "BUILD `factory/contract_scene.py` with one public function `build_contract_scene(package, scene_id: str) -> dict` (standard library plus the existing storygame.story_package models only; story-agnostic: no story, scene or character names in production code; pure; never mutates the package). "
    "It reads the loaded StoryPackage (`package.scenes` gives scene order, `package.knowledge_indexes` and `package.knowledge.knowledge` give items with `available_in_scenes`, `package.pacing.scenes` and `package.pacing.ending` give pacing windows and the ending; look at storygame/story_package/models.py and loader.py `_compile_knowledge_indexes`). Rules:\n"
    "- `id` is scene_id; raise ValueError for an unknown scene id.\n"
    "- `reveal_ids`: knowledge ids that are candidates in this scene (`scene_to_candidates[scene_id]`) and are NOT in `delivered_before`, sorted.\n"
    "- `delivered_before`, sorted: every knowledge id that is (a) available in at least one EARLIER scene (by `package.scenes` order) and not available in this scene, or (b) an entry item of this scene (`item.source.kind` is neither 'storylet_realization' nor 'canonical_route_event', so its source key is `entry:<scene>`; see the loader), because the engine delivers it on entry. An item available in both an earlier scene and this scene is NOT delivered_before by rule (a) (it can still be earned here).\n"
    "- `pacing_window`: the scene's `handoff_after_turns` from `package.pacing.scenes` if present, else None. `terminal`: true only if the package's pacing `ending` names this scene as its ending scene (read StoryEnding in models.py; if no field names a scene, set terminal false and say so in NOTES.txt). Other fields (`ending_requires`, `non_voiceable_says`, `unlearned_terms`, `epilogue_candidates`): `[]` for now, EXCEPT where the package gives them unambiguously; do not guess, record in NOTES.txt what you left empty.\n"
    "- The returned dict must have exactly the nine keys above and contain only str/int/bool/None/list/dict values (JSON serialisable).\n\n"
    "TESTS, WRITE THEM FIRST in tests/test_contract_scene.py (hermetic, no network, no model; load the real package with `load_story_package(default_package_root())` from storygame.story_package.loader and storygame.story_package.default_root; scene ids are read as `scene.scene_id` on `package.scenes`, which are in play order 1A..3C): "
    "(1) for the scene whose id ends 2C: `k_sl_2b_b_r4` is in delivered_before and not in reveal_ids; (2) for 2A: `k_scene_2a_entry` is in delivered_before; (3) for 1B: `k_sl_1a_b_r1` is in delivered_before; "
    "(4) the first scene has an empty set from rule (a); (5) unknown scene raises ValueError; (6) the result is JSON serialisable and building twice gives equal results; (7) the package is not mutated (compare a model_dump before and after); "
    "(8) integration: build the scene for 2C, then take a one-turn run whose grounding_ids are ['k_sl_2b_b_r4'] with outcome 'committed' (copy the turn field shape from the first case in tests/fixtures/outcome_contract/cases.json) and assert classify_run gives that turn knowledge_progress False. "
    "If any of (1)-(3) fails because the item is not shaped as assumed, read the package and adapt the RULE minimally, then say what you found in NOTES.txt; the three saved facts above are the requirement."
)
CHECK_B = (
    SETUP
    + ownership_guard(OWNED_B)
    + f"""start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs tests/test_contract_scene.py tests/test_outcome_contract.py 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -6
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || {{ echo "over the 120 s budget"; exit 1; }}
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
{PY} -m json.tool tests/shard_durations.json > /dev/null
grep -q '"tests/test_contract_scene.py"' tests/shard_durations.json || {{ echo "tests/shard_durations.json lacks the new test file"; exit 1; }}
grep -nE "k_sl_|k_scene_|SL-[0-9]|\\b[123][A-C]\\b" factory/contract_scene.py && {{ echo "story-specific ids in production code"; exit 1; }} || true
{PY} - <<'PYV'
import json
from pathlib import Path
from storygame.story_package.default_root import default_package_root
from storygame.story_package.loader import load_story_package
from factory.contract_scene import build_contract_scene
pkg = load_story_package(default_package_root())
s = build_contract_scene(pkg, "2C")
assert "k_sl_2b_b_r4" in s["delivered_before"] and "k_sl_2b_b_r4" not in s["reveal_ids"], s
assert "k_scene_2a_entry" in build_contract_scene(pkg, "2A")["delivered_before"]
assert "k_sl_1a_b_r1" in build_contract_scene(pkg, "1B")["delivered_before"]
assert set(s) == {{"id","pacing_window","terminal","reveal_ids","delivered_before","ending_requires","non_voiceable_says","unlearned_terms","epilogue_candidates"}}, set(s)
json.dumps(s)
print("contract scene OK for 2C, 2A, 1B")
PYV
"""
    + LINT
    + 'git diff --cached > "$WORK/out/contract-scene.patch"\ntest -s "$WORK/out/contract-scene.patch"\n'
)

manifest = {
    "run_name": "factory-28a-m4-fixture-and-contract-scene",
    "workdir": b.WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "m4-fixture",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1500,
            "check_timeout_s": 300,
            "ownership": OWNED_A,
            "spec": SPEC_A,
            "check": CHECK_A,
            "expect_files": [],
            "verified": "The M4 case uses a futile command, two new cases pin pressure beside an earned reveal and a pacing event caused by the command, 29 cases pass, every other case is unchanged.",
        },
        {
            "key": "contract-scene",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 400,
            "ownership": OWNED_B,
            "spec": SPEC_B,
            "check": CHECK_B,
            "expect_files": [],
            "verified": "build_contract_scene fills delivered_before from earlier scenes and entry items; the saved re-grounding cases in 2C, 2A and 1B are no longer read as new progress.",
        },
    ],
}
Path(__file__).with_name("round28a-m4-fixture-and-contract-scene-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
