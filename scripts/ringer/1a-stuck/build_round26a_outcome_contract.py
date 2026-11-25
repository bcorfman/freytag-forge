# ruff: noqa: E501
"""Round 26a: qualification Step 2 task 2.1: the pure outcome-contract classifier (core tier). Free, no model.

The frozen examples are written by the orchestrator and live in the qualification workspace; the worker copies them in
unchanged and the check compares them byte for byte, so the worker cannot weaken the examples.
"""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-26"
FIX = "/home/bcorfman/dev/ringer-work/qual-20261122/qualification/outcome_contract_fixtures"
OWNED = [
    "factory/outcome_contract.py",
    "tests/test_outcome_contract.py",
    "tests/fixtures/outcome_contract/cases.json",
    "tests/fixtures/outcome_contract/README.md",
    "tests/shard_durations.json",
]
README = Path(FIX, "README.md").read_text()

SPEC = b.COMMON + (
    "You may edit ONLY: " + ", ".join(OWNED) + ". No other production code, story data or existing test.\n\n"
    "BACKGROUND. The factory measures whether a blind player got stuck. Today the hosted path (frontend/e2e/blind-player.js), "
    "the bench probe (factory/stations/probe.py) and the qualification reader (factory/stations/live_playtest.py) each use a different "
    "definition of 'stuck', so zero flags does not mean zero stuck turns. You are writing the ONE pure function they will all call. "
    "You write only the new module and its tests; wiring it into the other paths is a later task, so do not edit them.\n\n"
    "STEP 1. Copy the frozen examples exactly: `mkdir -p tests/fixtures/outcome_contract && cp "
    f"{FIX}/cases.json {FIX}/README.md tests/fixtures/outcome_contract/`. NEVER edit those two files: the check compares them byte for byte "
    "with the originals, and an example you think is wrong is a finding for NOTES.txt, not something to change.\n\n"
    "STEP 2. Write factory/outcome_contract.py (pure functions, standard library only, no story, scene or character names, "
    "type-annotated, Python 3.12) exposing `classify_run(run: dict, scene: dict) -> dict`. The CONTRACT FOLLOWS in full; implement it exactly.\n"
    "-----\n" + README + "\n-----\n"
    'RESULT SHAPE `classify_run` returns: {"turns": [{"turn": int, "action_outcome": str, "knowledge_progress": bool|None, "authored_recovery": bool}], '
    '"confirmed_stuck": [int], "unresolved": [int], "provenance_flags": [], "exit": str, "status": str, "pacing": {}, '
    '"epilogue": {"offered": False, "taken": False}, "contract_version": "v1-core"}. This task implements the CORE tier only: '
    "`provenance_flags` is always [], `pacing` is {} and `epilogue` is the all-false object (a later task fills them in; mark each with a one-line comment). "
    "The `status` rule's `flagged` branch therefore cannot fire yet. Never mutate the inputs. Never raise on malformed input: a non-dict turn, a missing `turn` number, "
    "a non-list `turns`, wrong types for list fields all degrade to `unknown_telemetry`/`unresolved` for that turn (or an empty run), never an exception. "
    "Turn numbers in the output are the input's `turn` values; a duplicate or missing turn number makes that turn `unknown_telemetry`.\n\n"
    "STEP 3. Write tests/test_outcome_contract.py (hermetic, under 10 s): (a) parametrize over every case in cases.json whose `tier` is `core`, run `classify_run(case['run'], case['scene'])` and assert the subset comparison "
    "described under 'Comparing expected to actual' (write a small helper); each failure message names the case id and the field. Extension-tier cases must be skipped with a clear reason, not silently ignored. "
    "(b) Extra tests of your own: classify does not mutate its inputs (deepcopy compare); is deterministic; an empty `turns` list gives exit none, status healthy and no exception; "
    "malformed inputs (turns not a list, a turn that is a string, a turn with no `turn` key, `grounding_ids` that is a string) do not raise and give `unresolved`; "
    "a saved-report-shaped turn that lacks `committed_facts` and `null_grounding_ids` altogether (as today's reports do) is `unknown_telemetry` and makes the run `unresolved`, so no saved report can be certified yet; "
    "a stall run spanning a rejected turn; two separate stall runs in one run each judged on their own length; the window boundary (length == window is stuck, window-1 is not).\n\n"
    "STEP 4. Register the new test file: run `.venv/bin/python scripts/regen_shard_durations.py --missing-only` and keep only the one new entry in tests/shard_durations.json.\n\n"
    "If any frozen example contradicts the written rules, implement the example's expectation if it is the clearer reading of the rules, otherwise stop and describe the conflict in NOTES.txt; do not edit the examples."
)

OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)
CHECK = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
cmp tests/fixtures/outcome_contract/cases.json {FIX}/cases.json || {{ echo "cases.json differs from the frozen examples"; exit 1; }}
cmp tests/fixtures/outcome_contract/README.md {FIX}/README.md || {{ echo "README.md differs from the frozen contract"; exit 1; }}
git add -A -- factory tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/test_outcome_contract.py
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 60 s)"
[ "$took" -le 60 ] || {{ echo "over the 60 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
echo "ruff files: $PYFILES"
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
.venv/bin/python - <<'PYV'
import json
from factory.outcome_contract import classify_run
cases = json.load(open("tests/fixtures/outcome_contract/cases.json"))
core = [c for c in cases if c["tier"] == "core"]
assert len(core) == 19, len(core)
r = classify_run(core[0]["run"], core[0]["scene"])
assert set(["turns", "confirmed_stuck", "unresolved", "provenance_flags", "exit", "status", "pacing", "epilogue", "contract_version"]) <= set(r), sorted(r)
print("shape ok")
PYV
grep -q '"tests/test_outcome_contract.py"' tests/shard_durations.json || {{ echo "shard_durations has no entry for the new test file"; exit 1; }}
git diff --cached > "$WORK/out/outcome-contract-core.patch"
test -s "$WORK/out/outcome-contract-core.patch"
"""

manifest = {
    "run_name": "factory-26a-outcome-contract-core",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "outcome-contract-core",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 600,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "One pure classifier gives every run the same per-turn outcome, stuck list, exit and status, and the frozen examples pass byte-for-byte.",
        }
    ],
}
Path(__file__).with_name("round26a-outcome-contract-core-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
