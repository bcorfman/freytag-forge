# ruff: noqa: E501
"""Round 30a: test consolidation (owner request 2026-11-24). Task A: one table-driven test replaces the five per-scene
`test_existing_*_commands_still_reach_their_reveals` functions, with a shared scene harness. Task B: collapse the exact
structural duplicates found by an AST scan into parametrized tests in five files. Free, no model."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-30"
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
    return f"""git add -A -- tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({owned_re})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
"""


LINT = f"""PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
echo "ruff files: $PYFILES"
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
"""

RICHER = [
    "tests/test_richer_1c.py",
    "tests/test_richer_2a.py",
    "tests/test_richer_2b.py",
    "tests/test_richer_2c.py",
    "tests/test_richer_3a.py",
]
OWNED_A = [
    *RICHER,
    "tests/scene_harness.py",
    "tests/fixtures/scene_commands.json",
    "tests/test_scene_commands_reach_reveals.py",
    "tests/shard_durations.json",
]
SPEC_A = b.COMMON + (
    "You may edit ONLY these files: "
    + ", ".join(RICHER)
    + ", tests/scene_harness.py (new), tests/fixtures/scene_commands.json (new), tests/test_scene_commands_reach_reveals.py (new) and tests/shard_durations.json (one entry for the new test file, same format as its neighbours, value 3.0). "
    "No production code. Nothing else.\n\n"
    "PROBLEM. The owner finds that editing near-identical test functions takes too long. Each of the five files tests/test_richer_{1c,2a,2b,2c,3a}.py has a function named `test_existing_<scene>_commands_still_reach_their_reveals` that loops over `(true_facts, command, expected_reveal_id[, turn_index])` tuples, builds an engine with a file-local `_engine(...)` helper and asserts `_handoff(...)` finds the expected candidate. "
    "The `_engine` and `_handoff` helpers are copied in each file (1c and 2a are identical to each other; 2b, 2c and 3a are identical to each other and add `turn_index`).\n\n"
    "CHANGE, TEST FIRST.\n"
    "1. tests/scene_harness.py: `scene_engine(package, scene_id, *, true_facts=(), turn_index=0) -> tuple[RuntimeState, RuntimeEngine]` and `authored_handoff(engine, state, command)`, exactly the behaviour of the file-local helpers (copy their bodies; read all five files and confirm they match; if a file differs in a way that matters, keep that difference as a parameter and say so in NOTES.txt). "
    "Make the five files use it: replace each file's local `_engine` and `_handoff` bodies by thin wrappers (for example `def _engine(**kwargs): return scene_engine(PACKAGE, \"2B\", **kwargs)`) so no other test in those files has to change. Keep each file's other tests byte for byte.\n"
    '2. tests/fixtures/scene_commands.json: a JSON list of cases `{"scene": "1C", "true_facts": [...], "command": "...", "expected": "k_...", "turn_index": 0}` holding EXACTLY the tuples of the five old functions (1C 4, 2A 4, 2B 4, 2C 3, 3A 3 = 18 cases; for 2A and 3A build the fact lists the way the old functions did, e.g. expand `new_reveals` and `ARRIVED` into the literal fact ids; keep the case order of each old function).\n'
    "3. tests/test_scene_commands_reach_reveals.py: ONE parametrized test over that table (`pytest.param(..., id=\"<scene>-<expected>-<n>\")`), loading the real package once (module scope, `load_story_package(Path('data/stories/continuity-initiative'))` like the old files) and asserting what the old functions asserted, with the command in the failure message.\n"
    "4. Delete the five old `test_existing_*_commands_still_reach_their_reveals` functions and any import that becomes unused. Do not delete or change any other test.\n"
    "Run the five files and the new test. The five files must collect exactly 47 tests together (52 before minus the five removed) and the new file at least 18."
)
CHECK_A = (
    SETUP
    + ownership_guard(OWNED_A)
    + f"""start=$(date +%s)
before=$({PY} -m pytest --collect-only -q -p no:cacheprovider {" ".join(RICHER)} 2>/dev/null | grep -c '::')
echo "collected in the five richer files: $before"
[ "$before" -eq 47 ] || {{ echo "expected exactly 47 tests in the five files (52 minus the five old functions), got $before"; exit 1; }}
new=$({PY} -m pytest --collect-only -q -p no:cacheprovider tests/test_scene_commands_reach_reveals.py 2>/dev/null | grep -c '::')
[ "$new" -ge 18 ] || {{ echo "new test collects $new cases, need >= 18"; exit 1; }}
if grep -n "def test_existing_.*still_reach" {" ".join(RICHER)}; then echo "an old test_existing_* function is still present"; exit 1; fi
out=$({PY} -m pytest -q -p no:cacheprovider -rs -n 4 tests/test_scene_commands_reach_reveals.py {" ".join(RICHER)} 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -4
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
{PY} - <<'PYV'
import json
cases = json.load(open("tests/fixtures/scene_commands.json"))
from collections import Counter
c = Counter(x["scene"] for x in cases)
assert c == {{"1C": 4, "2A": 4, "2B": 4, "2C": 3, "3A": 3}}, c
assert all(set(x) >= {{"scene", "true_facts", "command", "expected"}} for x in cases)
PYV
cp tests/fixtures/scene_commands.json "$WORK/out/scene_commands.backup"
{PY} - <<'PYM'
import json
p = "tests/fixtures/scene_commands.json"
cases = json.load(open(p))
cases[0]["expected"] = "k_deliberately_wrong"
json.dump(cases, open(p, "w"))
PYM
if {PY} -m pytest -q -p no:cacheprovider tests/test_scene_commands_reach_reveals.py > "$WORK/out/mutation.txt" 2>&1; then echo "MUTATION SURVIVED: the table test passes with a wrong expected id"; cp "$WORK/out/scene_commands.backup" tests/fixtures/scene_commands.json; exit 1; fi
cp "$WORK/out/scene_commands.backup" tests/fixtures/scene_commands.json
echo "mutation check: the table test fails when an expected id is wrong"
{PY} -m pytest -q -p no:cacheprovider tests/test_scene_commands_reach_reveals.py 2>&1 | tail -2
took=$(( $(date +%s) - start ))
echo "took $took s (budget 360 s)"
[ "$took" -le 360 ] || {{ echo "over the 360 s budget"; exit 1; }}
grep -q '"tests/test_scene_commands_reach_reveals.py"' tests/shard_durations.json || {{ echo "shard_durations lacks the new test"; exit 1; }}
{PY} -m json.tool tests/shard_durations.json > /dev/null
git add -A -- tests
"""
    + LINT
    + 'git diff --cached > "$WORK/out/scene-commands.patch"\ntest -s "$WORK/out/scene-commands.patch"\n'
)

FILES_B = {
    "tests/test_narration_json_extract.py": (13, 13),
    "tests/story_source/test_l1_scene.py": (8, 8),
    "tests/test_speaker_presence.py": (11, 10),
    "tests/test_factory_guard.py": (30, 29),
    "tests/test_bench_item_facts.py": (241, 229),
}
OWNED_B = list(FILES_B)
SPEC_B = b.COMMON + (
    "You may edit ONLY: " + ", ".join(OWNED_B) + ". Nothing else (no new files, no production code).\n\n"
    "PROBLEM. The owner finds that editing near-identical test functions takes too long. An AST scan (same body after normalising constants, three or more functions, none already parametrized) found these groups; "
    'collapse each into ONE `@pytest.mark.parametrize` test whose cases keep the ORIGINAL inputs and expected values and whose `ids` keep the old test\'s meaning (use `pytest.param(..., id="<old name without the test_ prefix>")`):\n'
    "- tests/test_narration_json_extract.py: test_two_objects_are_ambiguous, test_no_object_is_not_extracted, test_empty_text_is_not_extracted (and any other function with the same skeleton you find in that file)\n"
    "- tests/story_source/test_l1_scene.py: test_unknown_scene_key, test_wrong_scene_value_type, test_wrong_scene_enum (and test_scene_id_pattern, test_missing_scene_key if their skeleton matches: patch one address, expect one L1 code)\n"
    "- tests/test_speaker_presence.py: test_plain_present_sentence_is_present, test_evidence_for_someone_else_does_not_inherit, test_non_evidence_predecessor_does_not_inherit\n"
    "- tests/test_factory_guard.py: test_wrong_effort_is_refused, test_unknown_station_is_refused, test_script_only_station_refuses_every_model\n"
    "- tests/test_bench_item_facts.py: test_held_by_pocket_place_keeps_holder, test_held_by_place_with_prefix_resolves, test_held_by_holders_area_keeps_holder\n"
    "Read each file first. If a candidate group differs in a way that matters (different assertion, different fixture), leave it alone and say so in NOTES.txt; never weaken an assertion, never drop a case, never merge tests that assert different things. "
    "Do not touch any other test. If a parametrized case needs a helper call, keep the helper as it is.\n\n"
    "Evidence the owner needs: after your change `pytest --collect-only -q` must report at least as many tests per file as before (before: "
    + ", ".join(f"{f.split('/')[-1]} {v[0]}" for f, v in FILES_B.items())
    + ") because every old function becomes one parameter case, and the number of `def test_` functions in the five files together must be at least 8 lower than now (now: "
    + ", ".join(f"{f.split('/')[-1]} {v[1]}" for f, v in FILES_B.items())
    + "). Run the five files."
)
CHECK_B = (
    SETUP
    + ownership_guard(OWNED_B)
    + "".join(
        f"""n=$({PY} -m pytest --collect-only -q -p no:cacheprovider {f} 2>/dev/null | grep -c '::')
echo "{f}: $n collected (before {v[0]})"
[ "$n" -ge {v[0]} ] || {{ echo "{f}: fewer tests collected than before"; exit 1; }}
"""
        for f, v in FILES_B.items()
    )
    + f"""defs=$(cat {" ".join(OWNED_B)} | grep -c '^def test_\\|^    def test_')
echo "def test_ functions now: $defs (before {sum(v[1] for v in FILES_B.values())})"
[ "$defs" -le {sum(v[1] for v in FILES_B.values()) - 8} ] || {{ echo "need at least 8 fewer test functions"; exit 1; }}
start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs -n 4 {" ".join(OWNED_B)} 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -4
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
took=$(( $(date +%s) - start ))
echo "took $took s (budget 240 s)"
[ "$took" -le 240 ] || {{ echo "over the 240 s budget"; exit 1; }}
"""
    + LINT
    + 'git diff --cached > "$WORK/out/dup-groups.patch"\ntest -s "$WORK/out/dup-groups.patch"\n'
)

manifest = {
    "run_name": "factory-30a-test-consolidation",
    "workdir": b.WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "scene-commands-table",
            "task_type": "code-refactor",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "ownership": OWNED_A,
            "spec": SPEC_A,
            "check": CHECK_A,
            "expect_files": [],
            "verified": "One table-driven test (18 cases) replaces the five per-scene functions, a shared harness replaces the copied helpers, and a wrong expected id makes it fail.",
        },
        {
            "key": "duplicate-groups",
            "task_type": "code-refactor",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 500,
            "ownership": OWNED_B,
            "spec": SPEC_B,
            "check": CHECK_B,
            "expect_files": [],
            "verified": "Exact structural duplicates in five files are parametrized with no fewer collected tests and at least eight fewer test functions.",
        },
    ],
}
Path(__file__).with_name("round30a-test-consolidation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
